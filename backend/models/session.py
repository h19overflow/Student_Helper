"""
Session domain models and schemas.

Request/response schemas for session operations.

Dependencies: pydantic
System role: Session API contracts
"""

from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class CreateSessionRequest(BaseModel):
    """Request schema for creating a new session."""

    metadata: dict = Field(default_factory=dict, description="Optional session metadata")


class SessionResponse(BaseModel):
    """Response schema for session operations."""

    id: uuid.UUID
    course_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict
