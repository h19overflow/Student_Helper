"""
Chat domain models and schemas.

Request/response schemas for chat operations.

Dependencies: pydantic
System role: Chat API contracts
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for chat messages."""

    message: str = Field(description="User question or message")
    include_diagram: bool = Field(default=False, description="Generate Mermaid diagram")


class ChatResponse(BaseModel):
    """Response schema for chat messages."""

    answer: str
    citations: list["Citation"]
    mermaid_diagram: str | None = None
