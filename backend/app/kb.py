import csv
import io
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import docx2txt
import pandas as pd
from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader
from qdrant_client.http import models

from app.db.qdrant import qdrant_db


KB_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KB_FILES_DIR = KB_DATA_DIR / "kb_files"
KB_META_FILE = KB_DATA_DIR / "knowledge_bases.json"


def _ensure_dirs():
    KB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    KB_FILES_DIR.mkdir(parents=True, exist_ok=True)
    if not KB_META_FILE.exists():
        KB_META_FILE.write_text(json.dumps({"knowledge_bases": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", name).strip("-").lower()
    return cleaned or f"kb-{uuid.uuid4().hex[:8]}"


def _read_store() -> Dict[str, Any]:
    _ensure_dirs()
    return json.loads(KB_META_FILE.read_text(encoding="utf-8"))


def _write_store(data: Dict[str, Any]):
    _ensure_dirs()
    KB_META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_embeddings(model: str):
    return OpenAIEmbeddings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE"),
        model=model,
        check_embedding_ctx_length=False,
    )


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    step = max(1, chunk_size - max(0, chunk_overlap))
    chunks: List[str] = []
    start = 0

    while start < len(cleaned):
        end = start + chunk_size
        piece = cleaned[start:end]
        if end < len(cleaned):
            breakpoints = [
                piece.rfind("\n\n"),
                piece.rfind("\n"),
                piece.rfind("。"),
                piece.rfind("！"),
                piece.rfind("？"),
                piece.rfind(". "),
                piece.rfind(" "),
            ]
            best_break = max(breakpoints)
            if best_break > int(chunk_size * 0.45):
                piece = piece[: best_break + 1]
                end = start + len(piece)

        piece = piece.strip()
        if piece:
            chunks.append(piece)

        if end >= len(cleaned):
            break
        start = max(start + 1, end - max(0, chunk_overlap))
        if start <= 0:
            start += step

    return chunks


def _split_by_markdown_heading(text: str, heading_marker: str) -> List[str]:
    lines = text.split("\n")
    sections: List[str] = []
    current: List[str] = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(heading_marker):
            if current:
                sections.append("\n".join(current).strip())
            current = [line]
            continue
        current.append(line)

    if current:
        sections.append("\n".join(current).strip())

    return [section for section in sections if section]


def _build_base_segments(text: str, separator: str) -> List[str]:
    normalized_separator = (separator or "").replace("\\n", "\n")
    stripped_separator = normalized_separator.strip()

    if stripped_separator and set(stripped_separator) == {"#"}:
        return _split_by_markdown_heading(text, stripped_separator)

    if normalized_separator:
        if normalized_separator == "\n":
            return [line.strip() for line in text.split("\n") if line.strip()]
        if normalized_separator in text:
            return [part.strip() for part in text.split(normalized_separator) if part.strip()]

    paragraph_segments = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    return paragraph_segments or [text.strip()]


def _split_text(text: str, chunk_size: int, chunk_overlap: int, separator: str = "\n\n") -> List[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    chunk_size = max(100, int(chunk_size or 800))
    chunk_overlap = max(0, min(int(chunk_overlap or 0), chunk_size // 2))
    base_segments = _build_base_segments(text, separator)

    chunks: List[str] = []
    current = ""

    for segment in base_segments:
        segment = segment.strip()
        if not segment:
            continue

        if len(segment) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(segment, chunk_size, chunk_overlap))
            continue

        candidate = f"{current}\n\n{segment}".strip() if current else segment
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())

        if chunk_overlap > 0 and chunks:
            overlap_text = chunks[-1][-chunk_overlap:].strip()
            current = f"{overlap_text}\n{segment}".strip() if overlap_text else segment
            if len(current) > chunk_size:
                chunks.extend(_split_long_text(current, chunk_size, chunk_overlap))
                current = ""
        else:
            current = segment

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def _decode_file(content: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        decoded = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(decoded))
        rows = [" | ".join(row) for row in reader]
        return "\n".join(rows)
    if suffix in {".txt", ".md", ".markdown", ".mdx", ".json", ".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".xml", ".yaml", ".yml", ".properties", ".html", ".htm", ".vtt"}:
        return content.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(page.strip() for page in pages if page.strip())
    if suffix == ".docx":
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as temp:
            temp.write(content)
            temp.flush()
            return docx2txt.process(temp.name) or ""
    if suffix in {".xlsx", ".xls"}:
        workbook = pd.read_excel(io.BytesIO(content), sheet_name=None)
        sheets: List[str] = []
        for sheet_name, df in workbook.items():
            sheet_text = df.fillna("").astype(str).apply(lambda row: " | ".join(row.tolist()), axis=1).tolist()
            joined_rows = "\n".join(row for row in sheet_text if row.strip())
            if joined_rows:
                sheets.append(f"## {sheet_name}\n{joined_rows}")
        return "\n\n".join(sheets)
    return content.decode("utf-8", errors="ignore")


class KnowledgeBaseService:
    def __init__(self):
        _ensure_dirs()
        self.client = qdrant_db.get_client()

    def _get_kb_embeddings(self, kb: Dict[str, Any]) -> OpenAIEmbeddings:
        model = kb.get("retrieval_config", {}).get("embedding_model") or "text-embedding-v4"
        return _get_embeddings(model)

    def _search_points(self, collection_name: str, query_vector: List[float], limit: int):
        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
            )

        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
            )
            points = getattr(response, "points", None)
            return points if points is not None else response

        raise AttributeError("当前 QdrantClient 不支持 search 或 query_points 接口")

    def _scroll_points(self, collection_name: str, file_id: str):
        flt = models.Filter(
            must=[
                models.FieldCondition(
                    key="file_id",
                    match=models.MatchValue(value=file_id),
                )
            ]
        )

        points: List[Any] = []
        offset = None
        while True:
            batch, next_offset = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=flt,
                limit=256,
                with_payload=True,
                with_vectors=False,
                offset=offset,
            )
            points.extend(batch)
            if next_offset is None:
                break
            offset = next_offset
        return points

    def list_kbs(self) -> List[Dict[str, Any]]:
        store = _read_store()
        return store["knowledge_bases"]

    def list_kb_summaries(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": kb["id"],
                "name": kb["name"],
                "icon": kb.get("icon", "🤖"),
                "description": kb.get("description", ""),
            }
            for kb in self.list_kbs()
        ]

    def create_kb(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = _read_store()
        kb_id = uuid.uuid4().hex[:10]
        collection_name = f"kb_{_slugify(payload['name'])}_{kb_id}"

        kb = {
            "id": kb_id,
            "name": payload["name"],
            "icon": payload.get("icon", "🤖"),
            "description": payload.get("description", ""),
            "permission": payload.get("permission", "只有我"),
            "segment_mode": payload.get("segment_mode", "general"),
            "index_mode": payload.get("index_mode", "high_quality"),
            "retrieval_mode": payload.get("retrieval_mode", "hybrid"),
            "chunk_config": {
                "separator": payload.get("separator", "\n\n"),
                "chunk_size": payload.get("chunk_size", 800),
                "chunk_overlap": payload.get("chunk_overlap", 100),
            },
            "retrieval_config": {
                "semantic_weight": payload.get("semantic_weight", 0.7),
                "keyword_weight": payload.get("keyword_weight", 0.3),
                "top_k": payload.get("top_k", 5),
                "score_threshold": payload.get("score_threshold", 0.2),
                "embedding_model": payload.get("embedding_model", "text-embedding-v4"),
            },
            "collection_name": collection_name,
            "vector_size": None,
            "created_at": _now(),
            "updated_at": _now(),
            "documents": [],
            "recall_history": [],
        }
        store["knowledge_bases"].insert(0, kb)
        _write_store(store)
        return kb

    def get_kb(self, kb_id: str) -> Dict[str, Any]:
        store = _read_store()
        for kb in store["knowledge_bases"]:
            if kb["id"] == kb_id:
                return kb
        raise KeyError("Knowledge base not found")

    def search_kbs(self, query: str, kb_ids: List[str], limit: int = 6) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        store = _read_store()
        selected = [kb for kb in store["knowledge_bases"] if kb["id"] in kb_ids and kb.get("vector_size")]
        results: List[Dict[str, Any]] = []

        for kb in selected:
            embeddings = self._get_kb_embeddings(kb)
            query_vector = embeddings.embed_query(query)
            hits = self._search_points(
                collection_name=kb["collection_name"],
                query_vector=query_vector,
                limit=min(limit, kb.get("retrieval_config", {}).get("top_k", limit) or limit),
            )
            for hit in hits:
                payload = getattr(hit, "payload", {}) or {}
                score = getattr(hit, "score", 0.0) or 0.0
                results.append(
                    {
                        "kb_id": kb["id"],
                        "kb_name": kb["name"],
                        "source": payload.get("source", "未知来源"),
                        "content": payload.get("page_content", ""),
                        "score": round(score, 4),
                        "chunk_index": payload.get("chunk_index", 0),
                    }
                )

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def update_kb(self, kb_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = _read_store()
        for kb in store["knowledge_bases"]:
            if kb["id"] != kb_id:
                continue
            previous_embedding_model = kb["retrieval_config"].get("embedding_model")
            kb["name"] = payload.get("name", kb["name"])
            kb["icon"] = payload.get("icon", kb["icon"])
            kb["description"] = payload.get("description", kb["description"])
            kb["permission"] = payload.get("permission", kb["permission"])
            kb["segment_mode"] = payload.get("segment_mode", kb["segment_mode"])
            kb["index_mode"] = payload.get("index_mode", kb["index_mode"])
            kb["retrieval_mode"] = payload.get("retrieval_mode", kb["retrieval_mode"])
            kb["chunk_config"].update({
                "separator": payload.get("separator", kb["chunk_config"]["separator"]),
                "chunk_size": payload.get("chunk_size", kb["chunk_config"]["chunk_size"]),
                "chunk_overlap": payload.get("chunk_overlap", kb["chunk_config"]["chunk_overlap"]),
            })
            kb["retrieval_config"].update({
                "semantic_weight": payload.get("semantic_weight", kb["retrieval_config"]["semantic_weight"]),
                "keyword_weight": payload.get("keyword_weight", kb["retrieval_config"]["keyword_weight"]),
                "top_k": payload.get("top_k", kb["retrieval_config"]["top_k"]),
                "score_threshold": payload.get("score_threshold", kb["retrieval_config"]["score_threshold"]),
                "embedding_model": payload.get("embedding_model", kb["retrieval_config"]["embedding_model"]),
            })
            if payload.get("embedding_model") and payload.get("embedding_model") != previous_embedding_model:
                kb["vector_size"] = None
            kb["updated_at"] = _now()
            _write_store(store)
            return kb
        raise KeyError("Knowledge base not found")

    def preview_chunks(self, text: str, separator: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        chunks = _split_text(text, chunk_size, chunk_overlap, separator)
        return [
            {"index": idx + 1, "content": chunk, "length": len(chunk)}
            for idx, chunk in enumerate(chunks[:20])
        ]

    def add_document(
        self,
        kb_id: str,
        filename: str,
        content: bytes,
        separator: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> Dict[str, Any]:
        store = _read_store()
        for kb in store["knowledge_bases"]:
            if kb["id"] != kb_id:
                continue

            raw_text = _decode_file(content, filename)
            chunks = _split_text(raw_text, chunk_size, chunk_overlap, separator)
            embeddings = self._get_kb_embeddings(kb)
            file_id = uuid.uuid4().hex[:10]
            kb_dir = KB_FILES_DIR / kb_id
            kb_dir.mkdir(parents=True, exist_ok=True)
            file_path = kb_dir / filename
            file_path.write_bytes(content)

            vectors = embeddings.embed_documents(chunks or [""])
            vector_size = len(vectors[0]) if vectors else 0
            if vector_size <= 0:
                raise ValueError("嵌入结果为空，无法写入知识库")

            if kb.get("vector_size") != vector_size:
                qdrant_db.recreate_collection(kb["collection_name"], vector_size=vector_size)
                kb["vector_size"] = vector_size
            points = []
            for idx, chunk in enumerate(chunks):
                point_id = abs(hash(f"{kb_id}:{file_id}:{idx}")) % (10**12)
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vectors[idx],
                        payload={
                            "page_content": chunk,
                            "source": filename,
                            "kb_id": kb_id,
                            "file_id": file_id,
                            "chunk_index": idx,
                        },
                    )
                )

            if points:
                self.client.upsert(collection_name=kb["collection_name"], points=points)

            doc = {
                "id": file_id,
                "name": filename,
                "segment_mode": "通用",
                "characters": len(raw_text),
                "chunks": len(chunks),
                "recall_count": 0,
                "uploaded_at": _now(),
                "status": "可用",
                "separator": separator,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            }
            kb["documents"].insert(0, doc)
            kb["updated_at"] = _now()
            _write_store(store)
            return doc

        raise KeyError("Knowledge base not found")

    def recall_test(self, kb_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
        store = _read_store()
        for kb in store["knowledge_bases"]:
            if kb["id"] != kb_id:
                continue

            if not kb.get("vector_size"):
                raise ValueError("当前知识库还没有可用向量，请先上传并处理文档")

            embeddings = self._get_kb_embeddings(kb)
            query_vector = embeddings.embed_query(query)
            results = self._search_points(
                collection_name=kb["collection_name"],
                query_vector=query_vector,
                limit=top_k,
            )
            formatted = [
                {
                    "source": hit.payload.get("source", "未知来源"),
                    "content": hit.payload.get("page_content", ""),
                    "score": round(hit.score, 4),
                    "chunk_index": hit.payload.get("chunk_index", 0),
                }
                for hit in results
            ]
            record = {
                "query": query,
                "tested_at": _now(),
                "results_count": len(formatted),
            }
            kb["recall_history"].insert(0, record)
            kb["recall_history"] = kb["recall_history"][:10]
            for result in formatted:
                for doc in kb["documents"]:
                    if doc["name"] == result["source"]:
                        doc["recall_count"] += 1
            kb["updated_at"] = _now()
            _write_store(store)
            return {"records": kb["recall_history"], "results": formatted}

        raise KeyError("Knowledge base not found")

    def get_document_chunks(self, kb_id: str, document_id: str) -> Dict[str, Any]:
        store = _read_store()
        for kb in store["knowledge_bases"]:
            if kb["id"] != kb_id:
                continue

            doc = next((item for item in kb["documents"] if item["id"] == document_id), None)
            if not doc:
                raise KeyError("Document not found")

            points = self._scroll_points(kb["collection_name"], document_id)
            chunks = []
            for point in points:
                payload = getattr(point, "payload", {}) or {}
                chunks.append(
                    {
                        "index": int(payload.get("chunk_index", 0)) + 1,
                        "content": payload.get("page_content", ""),
                        "length": len(payload.get("page_content", "")),
                    }
                )
            chunks.sort(key=lambda item: item["index"])
            return {
                "document": doc,
                "chunks": chunks,
            }

        raise KeyError("Knowledge base not found")


kb_service = KnowledgeBaseService()
