"""
Job domain models and schemas.

Request/response schemas for job tracking.

Dependencies: pydantic
System role: Job status API contracts
"""

from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class JobProgress(BaseModel):
    """Job progress details."""

    current: int = Field(description="Current progress count")
    total: int = Field(description="Total items to process")
    percentage: int = Field(description="Progress percentage (0-100)")


class JobStatusResponse(BaseModel):
    """Response schema for job status."""

    id: uuid.UUID
    task_id: str
    type: str
    status: str
    progress: JobProgress
    result: dict
    created_at: datetime
    updated_at: datetime
