"""
Chunk domain model.

Represents a document chunk with deterministic ID and embedding.

Dependencies: pydantic
System role: Document chunk data structure
"""

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Document chunk model."""

    id: str = Field(description="Deterministic chunk identifier (hash)")
    content: str = Field(description="Chunk text content")
    metadata: dict = Field(description="Chunk metadata (page, section, etc.)")
    embedding: list[float] | None = Field(default=None, description="Embedding vector")
