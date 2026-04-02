import os
from typing import List, Dict, Any
from app.db.qdrant import qdrant_db
from langchain_openai import OpenAIEmbeddings
from app.utils.logger import public_service_logger as logger

class RAGRetriever:
    """
    Retriever tool for Agents to query the Elevator Knowledge Base.
    """
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
            check_embedding_ctx_length=False,
        )
        self.client = qdrant_db.get_client()
        self.collection_name = os.getenv("QDRANT_COLLECTION", "elevator_kb")

    async def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Searches the knowledge base for the given query.
        """
        logger.info(f"RAG: Searching for: {query}")
        try:
            # Generate embedding for the query
            query_vector = self.embeddings.embed_query(query)
            
            # Search Qdrant
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            
            # Extract content from payload
            return [
                {
                    "content": hit.payload.get("page_content", ""),
                    "source": hit.payload.get("source", "Unknown"),
                    "score": hit.score
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"RAG: Search failed. Error: {e}")
            return []

# Singleton instance
retriever = RAGRetriever()
