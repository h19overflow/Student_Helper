"""
Streaming event schemas for WebSocket chat.

Defines event types and payloads for real-time chat streaming.

Dependencies: pydantic
System role: Streaming protocol schemas
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class StreamEventType(str, Enum):
    """Server-to-client event types for streaming chat."""

    CONNECTED = "connected"
    CONTEXT = "context"
    TOKEN = "token"
    CITATIONS = "citations"
    COMPLETE = "complete"
    ERROR = "error"


class ClientEventType(str, Enum):
    """Client-to-server event types."""

    CHAT = "chat"
    PING = "ping"


class StreamEvent(BaseModel):
    """
    Base streaming event model.

    Attributes:
        event: Event type identifier
        data: Event-specific payload
    """

    event: StreamEventType
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {"event": self.event.value, "data": self.data}


class ClientChatEvent(BaseModel):
    """
    Client chat message event payload.

    Attributes:
        message: User's chat message
        include_diagram: Whether to generate diagram
    """

    message: str
    include_diagram: bool = False


class ContextChunk(BaseModel):
    """
    Retrieved context chunk metadata.

    Attributes:
        chunk_id: Unique chunk identifier
        content_snippet: First 200 chars of content
        page: Source page number
        section: Source section name
        source_uri: Document source URI
        relevance_score: Similarity score
    """

    chunk_id: str
    content_snippet: str
    page: int | None = None
    section: str | None = None
    source_uri: str
    relevance_score: float


class StreamingCitation(BaseModel):
    """
    Citation extracted from retrieved context.

    Attributes:
        chunk_id: Source chunk identifier
        doc_name: Document filename
        page: Page number
        section: Section name
        source_uri: Full source URI
    """

    chunk_id: str
    doc_name: str
    page: int | None = None
    section: str | None = None
    source_uri: str
