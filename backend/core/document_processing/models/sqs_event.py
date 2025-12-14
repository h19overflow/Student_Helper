"""
SQS event message schema for document processing.

Defines the expected structure of SQS messages triggered by document uploads.

Dependencies: pydantic
System role: Data validation for Lambda SQS events
"""

from uuid import UUID

from pydantic import BaseModel, Field


class SQSEventSchema(BaseModel):
    """SQS message schema for document upload events."""

    document_id: UUID = Field(description="Document UUID")
    session_id: UUID = Field(description="Session UUID")
    s3_bucket: str = Field(description="S3 bucket name")
    s3_key: str = Field(description="S3 object key")
    filename: str = Field(description="Original filename")
