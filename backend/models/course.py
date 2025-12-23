"""
Course domain models and schemas.

Request/response schemas for course operations.

Dependencies: pydantic
System role: Course API contracts
"""

from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class CreateCourseRequest(BaseModel):
    """Request schema for creating a new course."""

    name: str = Field(..., min_length=1, max_length=255, description="Course name")
    description: str | None = Field(None, max_length=4096, description="Course description")
    metadata: dict = Field(default_factory=dict, description="Optional course metadata")


class UpdateCourseRequest(BaseModel):
    """Request schema for updating a course."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Course name")
    description: str | None = Field(None, max_length=4096, description="Course description")
    metadata: dict = Field(default_factory=dict, description="Optional course metadata")


class CourseResponse(BaseModel):
    """Response schema for course operations."""

    id: uuid.UUID
    name: str
    description: str | None
    metadata: dict
    created_at: datetime
    updated_at: datetime


class CourseDetailResponse(CourseResponse):
    """Response schema for course with session count."""

    session_count: int
