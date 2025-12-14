"""
Chat history adapter.

High-level business logic for chat history management.
Provides simple interface for adding/retrieving messages by role.

Dependencies: backend.boundary.db.CRUD.chat_history_crud
System role: Chat history business logic adapter
"""

from typing import List
from uuid import UUID

from langchain_core.messages import BaseMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.chat_history_crud import chat_history_crud


class ChatHistoryAdapter:
    """
    High-level adapter for chat history operations.

    Provides business logic layer on top of ChatHistoryCRUD.
    Simplifies adding messages by role (user/ai) and retrieving history.
    """

    def __init__(self, session_id: UUID, db: AsyncSession) -> None:
        """
        Initialize chat history adapter.

        Args:
            session_id: Session UUID for chat history scope
            db: AsyncSession for database operations
        """
        self.session_id = session_id
        self.db = db

    async def add_message(self, role: str, content: str) -> None:
        """
        Add message to chat history by role.

        Args:
            role: Message role ("user" or "ai")
            content: Message content

        Raises:
            ValueError: If role is not "user" or "ai", or session doesn't exist
        """
        if role.lower() == "user":
            await chat_history_crud.add_user_message(
                self.db,
                self.session_id,
                content,
            )
        elif role.lower() == "ai":
            await chat_history_crud.add_ai_message(
                self.db,
                self.session_id,
                content,
            )
        else:
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'ai'")

    async def add_user_message(self, content: str) -> None:
        """
        Add user message to chat history.

        Args:
            content: User message content

        Raises:
            ValueError: If session does not exist
        """
        await chat_history_crud.add_user_message(
            self.db,
            self.session_id,
            content,
        )

    async def add_ai_message(self, content: str) -> None:
        """
        Add AI message to chat history.

        Args:
            content: AI message content

        Raises:
            ValueError: If session does not exist
        """
        await chat_history_crud.add_ai_message(
            self.db,
            self.session_id,
            content,
        )

    async def get_messages(self, limit: int | None = None) -> List[BaseMessage]:
        """
        Get chat messages for session.

        Args:
            limit: Maximum number of recent messages to return (None = all)

        Returns:
            List of BaseMessage objects (HumanMessage, AIMessage)

        Raises:
            ValueError: If session does not exist
        """
        messages = await chat_history_crud.get_messages(self.db, self.session_id)

        if limit is not None and limit > 0:
            # Return most recent N messages
            return messages[-limit:]

        return messages

    async def get_messages_as_dicts(
        self,
        limit: int | None = None,
    ) -> List[dict]:
        """
        Get chat messages as dictionaries for API responses.

        Args:
            limit: Maximum number of recent messages to return (None = all)

        Returns:
            List of message dicts with keys: role, content, timestamp

        Raises:
            ValueError: If session does not exist
        """
        messages = await self.get_messages(limit)

        return [
            {
                "role": msg.type,  # "human" or "ai"
                "content": msg.content,
            }
            for msg in messages
        ]

    async def clear(self) -> None:
        """
        Clear all chat history for session.

        Raises:
            ValueError: If session does not exist
        """
        await chat_history_crud.clear_history(self.db, self.session_id)
