"""
Test suite for ChatService.

Tests chat message processing with RAG agent integration, chat history retrieval,
and message persistence. Uses mocked dependencies (db, RAGAgent, ChatHistoryAdapter).

System role: Verification of chat service orchestration layer
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.services.chat_service import ChatService
from backend.core.agentic_system.agent.rag_agent_schema import (
    RAGResponse,
    RAGCitation,
)


@pytest.fixture
def mock_db_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_session_id() -> uuid.UUID:
    """Provide sample session UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_rag_agent() -> MagicMock:
    """Provide mock RAG agent."""
    return AsyncMock()


@pytest.fixture
def sample_rag_response() -> RAGResponse:
    """Provide sample RAG response with citations."""
    return RAGResponse(
        answer="This is a test answer based on the context.",
        citations=[
            RAGCitation(
                chunk_id="chunk_1",
                content_snippet="Test content snippet",
                page=1,
                section="Introduction",
                source_uri="s3://bucket/document.pdf",
                relevance_score=0.95,
            )
        ],
        confidence=0.85,
        reasoning="Found matching information in the provided context.",
    )


@pytest.fixture
def chat_service(mock_db_session: AsyncSession, mock_rag_agent: MagicMock) -> ChatService:
    """Provide ChatService instance with mocked dependencies."""
    return ChatService(db=mock_db_session, rag_agent=mock_rag_agent)


class TestChatServiceInit:
    """Test suite for ChatService initialization."""

    def test_init_should_store_db_and_rag_agent(
        self, mock_db_session: AsyncSession, mock_rag_agent: MagicMock
    ) -> None:
        """Test ChatService stores db and rag_agent from constructor."""
        # Act
        service = ChatService(db=mock_db_session, rag_agent=mock_rag_agent)

        # Assert
        assert service.db is mock_db_session
        assert service.rag_agent is mock_rag_agent


class TestChatServiceProcessChat:
    """Test suite for ChatService.process_chat method."""

    @pytest.mark.asyncio
    async def test_process_chat_should_validate_session_exists(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat raises ValueError when session doesn't exist."""
        # Arrange
        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_get_session:
            # Act & Assert
            with pytest.raises(ValueError, match="does not exist"):
                await chat_service.process_chat(
                    session_id=sample_session_id,
                    message="Test question",
                )

            mock_get_session.assert_called_once_with(mock_db_session, sample_session_id)

    @pytest.mark.asyncio
    async def test_process_chat_should_fetch_chat_history(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat retrieves recent chat history."""
        # Arrange
        mock_session = MagicMock()
        chat_history = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = chat_history
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            await chat_service.process_chat(
                session_id=sample_session_id,
                message="Test question",
                context_window_size=10,
            )

            # Assert
            mock_adapter.get_messages.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_process_chat_should_invoke_rag_agent_with_history(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat passes chat history to RAG agent."""
        # Arrange
        mock_session = MagicMock()
        chat_history = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = chat_history
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            await chat_service.process_chat(
                session_id=sample_session_id,
                message="Test question",
                context_window_size=10,
            )

            # Assert
            chat_service.rag_agent.ainvoke.assert_called_once_with(
                question="Test question",
                session_id=str(sample_session_id),
                chat_history=chat_history,
            )

    @pytest.mark.asyncio
    async def test_process_chat_should_store_user_message(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat stores user message in history."""
        # Arrange
        mock_session = MagicMock()

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = []
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            await chat_service.process_chat(
                session_id=sample_session_id,
                message="Test question",
            )

            # Assert
            mock_adapter.add_user_message.assert_called_once_with("Test question")

    @pytest.mark.asyncio
    async def test_process_chat_should_store_ai_response(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat stores AI response in history."""
        # Arrange
        mock_session = MagicMock()

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = []
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            await chat_service.process_chat(
                session_id=sample_session_id,
                message="Test question",
            )

            # Assert
            mock_adapter.add_ai_message.assert_called_once_with(
                sample_rag_response.answer
            )

    @pytest.mark.asyncio
    async def test_process_chat_should_return_rag_response(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat returns RAG response."""
        # Arrange
        mock_session = MagicMock()

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = []
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            result = await chat_service.process_chat(
                session_id=sample_session_id,
                message="Test question",
            )

            # Assert
            assert result == sample_rag_response
            assert result.answer == sample_rag_response.answer
            assert len(result.citations) == 1

    @pytest.mark.asyncio
    async def test_process_chat_should_handle_empty_history(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat handles empty chat history correctly."""
        # Arrange
        mock_session = MagicMock()

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = []
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            result = await chat_service.process_chat(
                session_id=sample_session_id,
                message="First question",
            )

            # Assert
            chat_service.rag_agent.ainvoke.assert_called_once()
            call_args = chat_service.rag_agent.ainvoke.call_args
            assert call_args.kwargs["chat_history"] == []

    @pytest.mark.asyncio
    async def test_process_chat_should_respect_context_window_size(
        self,
        chat_service: ChatService,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test process_chat respects custom context_window_size."""
        # Arrange
        mock_session = MagicMock()

        with patch(
            "backend.application.services.chat_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.chat_service.ChatHistoryAdapter"
        ) as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter.get_messages.return_value = []
            mock_adapter.add_user_message = AsyncMock()
            mock_adapter.add_ai_message = AsyncMock()

            chat_service.rag_agent.ainvoke.return_value = sample_rag_response

            # Act
            await chat_service.process_chat(
                session_id=sample_session_id,
                message="Test question",
                context_window_size=20,
            )

            # Assert
            mock_adapter.get_messages.assert_called_once_with(limit=20)
