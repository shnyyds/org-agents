import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

class QdrantDB:
    """
    Qdrant Vector Database Client for RAG and Knowledge Base storage.
    """
    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", 6333))
        self.client = QdrantClient(host=self.host, port=self.port)
        self.default_collection = os.getenv("QDRANT_COLLECTION", "elevator_kb")

    def create_collection(self, collection_name: str = None, vector_size: int = 1536):
        """
        Creates a new collection in Qdrant if it doesn't exist.
        Default vector size is for OpenAI embeddings (1536).
        """
        name = collection_name or self.default_collection
        
        # Check if collection exists
        collections = self.client.get_collections().collections
        exists = any(c.name == name for c in collections)
        
        if not exists:
            print(f"Creating collection: {name}")
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
        else:
            print(f"Collection {name} already exists.")

    def recreate_collection(self, collection_name: str, vector_size: int):
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if exists:
            self.client.delete_collection(collection_name=collection_name)
        self.create_collection(collection_name=collection_name, vector_size=vector_size)

    def get_client(self):
        return self.client

# Singleton instance
qdrant_db = QdrantDB()
