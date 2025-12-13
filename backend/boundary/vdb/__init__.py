"""
Vector database boundary layer.

Provides S3 Vectors client for vector storage and retrieval operations.
Handles embedding upsert, similarity search, and metadata filtering.

Dependencies: boto3, backend.configs
System role: Vector store adapter for RAG retrieval
"""

from backend.boundary.vdb.vector_store_client import VectorStoreClient
from backend.boundary.vdb.vector_schemas import VectorQuery, VectorMetadata, VectorSearchResult

__all__ = [
    "VectorStoreClient",
    "VectorQuery",
    "VectorMetadata",
    "VectorSearchResult",
]
