"""
Vector database schemas.

Pydantic models for vector operations (queries, metadata, results).
Used for type-safe vector store interactions.

Dependencies: pydantic
System role: Type definitions for vector operations
"""

from typing import Any
from pydantic import BaseModel, Field
import uuid


class VectorMetadata(BaseModel):
    """
    Metadata attached to each vector.

    All fields marked as filterable in VectorStoreSettings
    can be used for metadata filtering during retrieval.
    """

    session_id: uuid.UUID = Field(description="Session ID for isolation")
    doc_id: uuid.UUID = Field(description="Document ID for @doc routing")
    chunk_id: str = Field(description="Deterministic chunk identifier")
    page: int | None = Field(default=None, description="Page number in source document")
    section: str | None = Field(default=None, description="Section heading or title")
    source_uri: str = Field(description="Source file URI or URL")


class VectorQuery(BaseModel):
    """Query parameters for vector search."""

    embedding: list[float] = Field(description="Query embedding vector")
    top_k: int = Field(default=5, description="Number of results to return", ge=1, le=100)
    session_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by session ID (enforced if enabled in config)",
    )
    doc_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by document ID for @doc mentions",
    )
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class VectorSearchResult(BaseModel):
    """Single result from vector search."""

    chunk_id: str = Field(description="Chunk identifier")
    content: str = Field(description="Chunk text content")
    metadata: VectorMetadata = Field(description="Chunk metadata")
    similarity_score: float = Field(description="Similarity score (0.0-1.0)")
