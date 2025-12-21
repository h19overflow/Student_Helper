"""
SQS event schema for document processing.

Validates messages received from SQS when documents are uploaded.
Each message contains metadata needed by the pipeline.

Dependencies: pydantic
System role: Data validation and contract definition
"""

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class DocumentMetadata(BaseModel):
    """Document metadata extracted from S3 upload notification."""

    document_id: UUID = Field(..., description="Document ID from RDS")
    session_id: UUID = Field(..., description="Session ID for isolation")
    s3_key: str = Field(..., description="S3 object key (bucket/session/filename)")
    filename: str = Field(..., description="Original filename for logging")
    file_size_bytes: int = Field(..., description="File size for validation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "s3_key": "documents/550e8400-e29b-41d4-a716-446655440001/resume.pdf",
                "filename": "resume.pdf",
                "file_size_bytes": 1024000,
            }
        }
    )


class SQSEventSchema(BaseModel):
    """SQS message body for document processing events."""

    document_id: UUID
    session_id: UUID
    s3_key: str
    filename: str
    file_size_bytes: int

    @classmethod
    def from_document_metadata(cls, metadata: DocumentMetadata) -> "SQSEventSchema":
        """Create schema from document metadata."""
        return cls(
            document_id=metadata.document_id,
            session_id=metadata.session_id,
            s3_key=metadata.s3_key,
            filename=metadata.filename,
            file_size_bytes=metadata.file_size_bytes,
        )


class SQSRecord(BaseModel):
    """Single SQS record wrapper."""

    messageId: str
    receiptHandle: str
    body: str  # JSON string containing SQSEventSchema
    attributes: dict
    messageAttributes: dict = {}
    md5OfBody: str


class SQSEvent(BaseModel):
    """Complete SQS Lambda event."""

    Records: list[SQSRecord]
