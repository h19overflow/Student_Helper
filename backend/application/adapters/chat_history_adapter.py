"""
Chat history adapter.

Wraps LangChain PostgresChatMessageHistory for session-based chat.

Dependencies: langchain, backend.boundary.db
System role: Chat history persistence adapter
"""

import uuid


class ChatHistoryAdapter:
    """Chat history adapter for LangChain integration."""

    def __init__(self, session_id: uuid.UUID) -> None:
        """Initialize chat history adapter."""
        pass

    def add_message(self, role: str, content: str) -> None:
        """Add message to chat history."""
        pass

    def get_messages(self, limit: int = 10) -> list[dict]:
        """Get recent chat messages."""
        pass

    def clear(self) -> None:
        """Clear chat history."""
        pass
