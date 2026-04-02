import os
import sys
from pathlib import Path

# Add the backend directory to the path so we can import app
sys.path.append(str(Path(__file__).parent.parent))

from app.db.qdrant import qdrant_db
from app.utils.logger import elevator_logger as logger
from langchain_community.document_loaders import TextLoader, BSHTMLLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client.http import models

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def ingest_documents():
    """
    Ingests all documentation from the docs/ directory into Qdrant.
    """
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    logger.info(f"Ingesting documents from: {docs_dir}")

    # Initialize components
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE"),
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
        check_embedding_ctx_length=False,
    )
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    # Create collection
    qdrant_db.create_collection(vector_size=1536) # Standard size for v3-small
    client = qdrant_db.get_client()
    collection_name = os.getenv("QDRANT_COLLECTION", "elevator_kb")

    all_docs = []

    # Process each file type
    for file_path in docs_dir.glob("*"):
        logger.info(f"Processing: {file_path.name}")
        try:
            if file_path.suffix == ".html":
                loader = BSHTMLLoader(str(file_path))
            elif file_path.suffix == ".docx":
                loader = Docx2txtLoader(str(file_path))
            elif file_path.suffix == ".xlsx":
                # Note: UnstructuredExcelLoader requires 'unstructured' and 'openpyxl'
                loader = UnstructuredExcelLoader(str(file_path))
            elif file_path.suffix == ".txt" or file_path.suffix == ".md":
                loader = TextLoader(str(file_path))
            else:
                logger.warning(f"Skipping unsupported file type: {file_path.suffix}")
                continue
            
            loaded_docs = loader.load()
            split_docs = text_splitter.split_documents(loaded_docs)
            
            # Add metadata
            for d in split_docs:
                d.metadata["source"] = file_path.name
                
            all_docs.extend(split_docs)
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")

    if not all_docs:
        logger.warning("No documents found to ingest.")
        return

    # Batch upload to Qdrant
    logger.info(f"Uploading {len(all_docs)} chunks to Qdrant...")
    
    texts = [d.page_content for d in all_docs]
    metadatas = [d.metadata for d in all_docs]
    
    # Simple upload using LangChain's Qdrant integration would be easier, 
    # but let's stick to the client for full control.
    
    # Generate embeddings
    vector_embeddings = embeddings.embed_documents(texts)
    
    # Prepare points
    points = [
        models.PointStruct(
            id=i,
            vector=vector_embeddings[i],
            payload={
                "page_content": texts[i],
                **metadatas[i]
            }
        ) for i in range(len(texts))
    ]
    
    # Upsert in batches of 100
    for i in range(0, len(points), 100):
        batch = points[i:i+100]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        
    logger.info("Ingestion complete.")

if __name__ == "__main__":
    ingest_documents()
