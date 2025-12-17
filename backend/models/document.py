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


class PresignedUrlRequest(BaseModel):
    """Request schema for generating presigned upload URL."""

    filename: str = Field(description="Original filename from user")
    content_type: str = Field(
        default="application/octet-stream",
        description="MIME type of the file",
    )


class PresignedUrlResponse(BaseModel):
    """Response schema with presigned URL for direct S3 upload."""

    presigned_url: str = Field(description="URL for uploading file to S3")
    s3_key: str = Field(description="S3 object key (needed for upload notification)")
    expires_at: str = Field(description="ISO timestamp when URL expires")
    content_type: str = Field(description="Content type to use in upload")


class DocumentUploadedNotification(BaseModel):
    """Request schema for notifying backend that upload to S3 is complete."""

    s3_key: str = Field(description="S3 object key from presigned URL response")
    filename: str = Field(description="Original filename")
