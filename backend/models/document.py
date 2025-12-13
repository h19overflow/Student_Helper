"""
Document domain models and schemas.

Request/response schemas for document operations.

Dependencies: pydantic
System role: Document API contracts
"""

from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class UploadDocumentsRequest(BaseModel):
    """Request schema for uploading documents."""

    files: list[str] = Field(description="List of file URLs or paths")


class DocumentResponse(BaseModel):
    """Response schema for document operations."""

    id: uuid.UUID
    session_id: uuid.UUID
    name: str
    status: str
    created_at: datetime
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""

    documents: list[DocumentResponse]
    total: int
    cursor: str | None = None
