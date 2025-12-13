"""
Common response models and utilities.

Generic response wrappers and error schemas.

Dependencies: pydantic
System role: Common API response structures
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""

    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error: str = Field(description="Error message")
    details: dict | None = Field(default=None, description="Additional error context")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[T]
    total: int
    cursor: str | None = None
    has_more: bool = False
