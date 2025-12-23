"""
Configuration settings for document processing pipeline.

Provides environment-based configuration for parsing, chunking, embedding, and saving.

Dependencies: pydantic, pydantic_settings
System role: Centralized pipeline configuration
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentPipelineSettings(BaseSettings):
    """Settings for document ingestion pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="DOC_PIPELINE_",
        case_sensitive=False,
        extra="ignore",
    )

    # AWS S3 Vectors bucket region
    bedrock_region: str = Field(
        default="ap-southeast-2",
        description="AWS region for S3 Vectors bucket",
    )
    embedding_region: str = Field(
        default="us-east-1",
        description="Unused - kept for backwards compatibility",
    )
    embedding_model_id: str = Field(
        default="text-embedding-004",
        description="Google Gemini embedding model ID (1024 dimensions)",
    )

    # Chunking settings
    chunk_size: int = Field(
        default=1000,
        description="Maximum chunk size in characters",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between consecutive chunks",
    )

    # S3 Vectors settings
    vectors_bucket: str = Field(
        default="student-helper-dev-vectors",
        description="S3 Vectors bucket name",
    )
    vectors_index: str = Field(
        default="documents",
        description="S3 Vectors index name within the bucket",
    )

    # S3 Documents bucket (for raw document storage)
    documents_bucket: str = Field(
        default="student-helper-dev-documents",
        description="S3 bucket for raw document storage",
    )

    # Database settings (for RDS status updates)
    database_url: str = Field(
        default="",
        description="PostgreSQL connection string",
    )

    # Output settings (DEPRECATED - use S3 Vectors instead)
    output_directory: str = Field(
        default="./data/processed",
        description="Directory for local JSON output (deprecated)",
    )


@lru_cache
def get_pipeline_settings() -> DocumentPipelineSettings:
    """
    Get cached pipeline settings instance.

    Returns:
        DocumentPipelineSettings: Singleton settings loaded from environment
    """
    return DocumentPipelineSettings()
