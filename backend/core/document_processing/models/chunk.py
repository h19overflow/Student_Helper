"""
Chunk domain model for document processing pipeline.

Represents a document chunk with deterministic ID, content, metadata, and embedding.

Dependencies: pydantic
System role: Data structure for document chunks in ingestion pipeline
"""

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Document chunk with optional embedding vector."""

    id: str = Field(description="Deterministic chunk identifier (content hash)")
    content: str = Field(description="Chunk text content")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata (page, section, source)")
    embedding: list[float] | None = Field(default=None, description="Embedding vector")
