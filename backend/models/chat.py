"""
Chat domain models and schemas.

Request/response schemas for chat operations.

Dependencies: pydantic
System role: Chat API contracts
"""

from pydantic import BaseModel, Field

from backend.models.citation import Citation


class ChatRequest(BaseModel):
    """Request schema for chat messages."""

    message: str = Field(description="User question or message")
    include_diagram: bool = Field(default=False, description="Generate Mermaid diagram")


class ChatResponse(BaseModel):
    """Response schema for chat messages."""

    answer: str
    citations: list[Citation]
    mermaid_diagram: str | None = None


class ChatMessageResponse(BaseModel):
    """Single chat message in history."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""

    messages: list[ChatMessageResponse]
    total: int = Field(description="Total number of messages")


# Ensure forward references are resolved
ChatResponse.model_rebuild()
