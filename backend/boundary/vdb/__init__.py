"""
Vector database boundary layer.

Provides vector store clients for storage and retrieval operations.
- VectorStoreClient: Production S3 Vectors client
- FAISSStore: Local development FAISS client

Dependencies: boto3, langchain_community, langchain_aws
System role: Vector store adapter for RAG retrieval
"""

from backend.boundary.vdb.vector_schemas import VectorQuery, VectorMetadata, VectorSearchResult


def get_vector_store_client():
    """Lazy import for VectorStoreClient to avoid circular imports."""
    from backend.boundary.vdb.vector_store_client import VectorStoreClient
    return VectorStoreClient


def get_faiss_store():
    """Lazy import for FAISSStore to avoid circular imports."""
    from backend.boundary.vdb.faiss_store import FAISSStore
    return FAISSStore


def get_dev_pipeline():
    """Lazy import for DevDocumentPipeline to avoid circular imports."""
    from backend.boundary.vdb.dev_task import DevDocumentPipeline, DevPipelineResult
    return DevDocumentPipeline, DevPipelineResult


__all__ = [
    "VectorQuery",
    "VectorMetadata",
    "VectorSearchResult",
    "get_vector_store_client",
    "get_faiss_store",
    "get_dev_pipeline",
]
