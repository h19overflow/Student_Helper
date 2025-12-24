"""
Vector store configuration settings.

Manages S3 Vectors configuration for vector storage and retrieval.
Includes embedding model settings and metadata filtering configuration.

Dependencies: pydantic, pydantic_settings
System role: Vector database configuration for RAG retrieval
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class VectorStoreSettings(BaseSettings):
    """Vector store configuration (FAISS for dev, S3 Vectors for prod)."""

    store_type: str = Field(
        default="s3",
        description="Vector store type: 'faiss' for local dev, 's3' for production",
    )
    aws_region: str = Field(default="ap-southeast-2", description="AWS region for S3 Vectors")
    embedding_region: str = Field(
        default="us-east-1",
        description="Unused - kept for backwards compatibility",
    )
    index_name: str = Field(default="documents", description="S3 Vectors index name")

    embedding_model: str = Field(
        default="models/gemini-embedding-001",
        description="Google Gemini embedding model ID (gemini-embedding-001 supports 1024-dim)",
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Embedding vector dimension (1024 for S3 Vectors index compatibility)",
    )

    top_k: int = Field(default=5, description="Number of top results to retrieve")
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score for retrieval (0.0-1.0)",
    )

    # Metadata filtering
    enable_session_filtering: bool = Field(
        default=True,
        description="Enforce session_id filtering on all queries",
    )
    filterable_metadata_fields: list[str] = Field(
        default=["session_id", "doc_id", "page"],
        description="Metadata fields available for filtering",
    )

    class Config:
        """Pydantic config."""

        env_prefix = "VECTOR_STORE_"
        case_sensitive = False
