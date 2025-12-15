"""
Chat history CRUD operations.

Wraps LangChain PostgresChatMessageHistory for session-scoped chat persistence.
Uses psycopg directly (not SQLAlchemy) as required by langchain_postgres.

Dependencies: langchain_postgres, psycopg, backend.configs
System role: Chat message persistence using PostgresChatMessageHistory
"""

from typing import List
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_postgres import PostgresChatMessageHistory
import psycopg
from sqlalchemy.ext.asyncio import AsyncSession

from backend.configs import get_settings
from backend.boundary.db.CRUD.session_crud import session_crud


class ChatHistoryCRUD:
    """
    CRUD operations for chat message history using PostgresChatMessageHistory.

    All operations are session-scoped - messages belong to a specific session.
    Uses psycopg connections as required by langchain_postgres.
    """

    TABLE_NAME = "chat_messages"

    def __init__(self) -> None:
        """Initialize ChatHistoryCRUD with database settings."""
        settings = get_settings()
        self.connection_string = settings.database.database_url

    async def _validate_session_exists(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> None:
        """
        Validate that session exists in database.

        Args:
            db: AsyncSession for session lookup
            session_id: Session UUID to validate

        Raises:
            ValueError: If session does not exist
        """
        session = await session_crud.get_by_id(db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")

    def _get_chat_history(self, session_id: UUID) -> PostgresChatMessageHistory:
        """
        Create PostgresChatMessageHistory instance for session.

        Args:
            session_id: Session UUID

        Returns:
            PostgresChatMessageHistory instance scoped to session
        """
        # Use synchronous connection for now
        # TODO: Migrate to async when langchain_postgres async is stable
        sync_connection = psycopg.connect(self.connection_string)

        # table_name and session_id are positional-only in newer langchain_postgres
        return PostgresChatMessageHistory(
            self.TABLE_NAME,
            str(session_id),
            sync_connection=sync_connection,
        )

    async def add_user_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        content: str,
    ) -> None:
        """
        Add user message to chat history.

        Args:
            db: AsyncSession for session validation
            session_id: Session UUID
            content: User message content

        Raises:
            ValueError: If session does not exist
        """
        await self._validate_session_exists(db, session_id)

        chat_history = self._get_chat_history(session_id)
        chat_history.add_messages([HumanMessage(content=content)])

    async def add_ai_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        content: str,
    ) -> None:
        """
        Add AI message to chat history.

        Args:
            db: AsyncSession for session validation
            session_id: Session UUID
            content: AI message content

        Raises:
            ValueError: If session does not exist
        """
        await self._validate_session_exists(db, session_id)

        chat_history = self._get_chat_history(session_id)
        chat_history.add_messages([AIMessage(content=content)])

    async def get_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> List[BaseMessage]:
        """
        Retrieve all messages for session.

        Args:
            db: AsyncSession for session validation
            session_id: Session UUID

        Returns:
            List of BaseMessage objects (HumanMessage, AIMessage, SystemMessage)

        Raises:
            ValueError: If session does not exist
        """
        await self._validate_session_exists(db, session_id)

        chat_history = self._get_chat_history(session_id)
        return chat_history.messages

    async def clear_history(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> None:
        """
        Delete all messages for session.

        Args:
            db: AsyncSession for session validation
            session_id: Session UUID

        Raises:
            ValueError: If session does not exist
        """
        await self._validate_session_exists(db, session_id)

        chat_history = self._get_chat_history(session_id)
        chat_history.clear()

    @classmethod
    def create_table(cls) -> None:
        """
        Create chat_messages table schema (one-time setup).

        Should be run during database initialization.
        Creates table with columns: id, session_id, message, created_at
        """
        settings = get_settings()
        connection_string = settings.database.database_url

        with psycopg.connect(connection_string) as conn:
            # Positional argument for table_name in newer langchain_postgres
            PostgresChatMessageHistory.create_tables(conn, cls.TABLE_NAME)


chat_history_crud = ChatHistoryCRUD()
