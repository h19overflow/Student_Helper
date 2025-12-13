"""
Citation domain model.

Represents a citation to source document for grounded answers.

Dependencies: pydantic
System role: Citation data structure
"""

from pydantic import BaseModel, Field
import uuid


class Citation(BaseModel):
    """Citation model for source attribution."""

    doc_name: str = Field(description="Source document name")
    page: int | None = Field(default=None, description="Page number in source")
    section: str | None = Field(default=None, description="Section heading")
    chunk_id: str = Field(description="Chunk identifier for tracing")
    source_uri: str = Field(description="Source file URI")
