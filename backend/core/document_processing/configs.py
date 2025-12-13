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

    # Google API settings
    google_api_key: str = Field(
        default="",
        description="Google API key for Gemini embeddings",
    )

    # Embedding settings
    embedding_model: str = Field(
        default="models/gemini-embedding-001",
        description="Google Gemini embedding model name",
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

    # Output settings
    output_directory: str = Field(
        default="./data/processed",
        description="Directory for local JSON output",
    )


@lru_cache
def get_pipeline_settings() -> DocumentPipelineSettings:
    """
    Get cached pipeline settings instance.

    Returns:
        DocumentPipelineSettings: Singleton settings loaded from environment
    """
    return DocumentPipelineSettings()
