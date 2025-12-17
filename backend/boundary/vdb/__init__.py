"""
Vector database boundary layer.

Provides vector store clients for storage and retrieval operations.
- S3VectorsStore: Production S3 Vectors client (LangChain integration)

Dependencies: langchain_aws
System role: Vector store adapter for RAG retrieval
"""

from backend.boundary.vdb.vector_schemas import VectorQuery, VectorMetadata, VectorSearchResult


def get_s3_vectors_store():
    """Lazy import for S3VectorsStore to avoid circular imports."""
    from backend.boundary.vdb.s3_vectors_store import S3VectorsStore
    return S3VectorsStore


__all__ = [
    "VectorQuery",
    "VectorMetadata",
    "VectorSearchResult",
    "get_s3_vectors_store",
]
