"""
Test suite for ChatHistoryAdapter business logic layer.

Tests high-level chat history operations including adding messages by role,
retrieving messages with optional limits, converting to dictionaries,
and clearing history. Uses async fixtures with mocked ChatHistoryCRUD.

System role: Verification of chat history business logic adapter
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.adapters.chat_history_adapter import ChatHistoryAdapter


@pytest.fixture
def mock_db_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_session_id() -> uuid.UUID:
    """Provide sample session UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def chat_history_adapter(
    sample_session_id: uuid.UUID, mock_db_session: AsyncSession
) -> ChatHistoryAdapter:
    """Provide ChatHistoryAdapter instance for testing."""
    return ChatHistoryAdapter(sample_session_id, mock_db_session)


class TestChatHistoryAdapterInit:
    """Test suite for ChatHistoryAdapter initialization."""

    def test_init_should_store_session_id(
        self, sample_session_id: uuid.UUID, mock_db_session: AsyncSession
    ) -> None:
        """Test ChatHistoryAdapter stores session_id from constructor."""
        # Act
        adapter = ChatHistoryAdapter(sample_session_id, mock_db_session)

        # Assert
        assert adapter.session_id == sample_session_id

    def test_init_should_store_db_session(
        self, sample_session_id: uuid.UUID, mock_db_session: AsyncSession
    ) -> None:
        """Test ChatHistoryAdapter stores db AsyncSession from constructor."""
        # Act
        adapter = ChatHistoryAdapter(sample_session_id, mock_db_session)

        # Assert
        assert adapter.db == mock_db_session


class TestChatHistoryAdapterAddMessage:
    """Test suite for ChatHistoryAdapter.add_message() method."""

    @pytest.mark.asyncio
    async def test_add_message_with_user_role_should_call_add_user_message(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message delegates to add_user_message when role is 'user'."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_user_message = AsyncMock()

            # Act
            await chat_history_adapter.add_message("user", "Hello AI")

            # Assert
            mock_crud.add_user_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_with_ai_role_should_call_add_ai_message(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message delegates to add_ai_message when role is 'ai'."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_ai_message = AsyncMock()

            # Act
            await chat_history_adapter.add_message("ai", "Hello human")

            # Assert
            mock_crud.add_ai_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_with_lowercase_user_role(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message is case-insensitive for 'user' role."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_user_message = AsyncMock()

            # Act
            await chat_history_adapter.add_message("USER", "Hello AI")

            # Assert
            mock_crud.add_user_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_with_lowercase_ai_role(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message is case-insensitive for 'ai' role."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_ai_message = AsyncMock()

            # Act
            await chat_history_adapter.add_message("AI", "Hello human")

            # Assert
            mock_crud.add_ai_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_should_raise_for_invalid_role(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message raises ValueError for invalid role."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await chat_history_adapter.add_message("assistant", "Hello")

        assert "Invalid role" in str(exc_info.value)
        assert "assistant" in str(exc_info.value)
        assert "user" in str(exc_info.value).lower()
        assert "ai" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_message_should_raise_for_empty_role(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message raises ValueError for empty role string."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await chat_history_adapter.add_message("", "Hello")

        assert "Invalid role" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_message_should_raise_for_none_role(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_message raises error when role is None."""
        # Act & Assert
        with pytest.raises((ValueError, AttributeError)):
            await chat_history_adapter.add_message(None, "Hello")


class TestChatHistoryAdapterAddUserMessage:
    """Test suite for ChatHistoryAdapter.add_user_message() method."""

    @pytest.mark.asyncio
    async def test_add_user_message_should_delegate_to_crud(
        self,
        chat_history_adapter: ChatHistoryAdapter,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test add_user_message delegates to ChatHistoryCRUD."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_user_message = AsyncMock()

            # Act
            await chat_history_adapter.add_user_message("Test message")

            # Assert
            mock_crud.add_user_message.assert_called_once_with(
                mock_db_session, sample_session_id, "Test message"
            )

    @pytest.mark.asyncio
    async def test_add_user_message_should_propagate_session_validation_error(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_user_message propagates ValueError from CRUD layer."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_user_message = AsyncMock(
                side_effect=ValueError("Session not found")
            )

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_adapter.add_user_message("Test")

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryAdapterAddAIMessage:
    """Test suite for ChatHistoryAdapter.add_ai_message() method."""

    @pytest.mark.asyncio
    async def test_add_ai_message_should_delegate_to_crud(
        self,
        chat_history_adapter: ChatHistoryAdapter,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test add_ai_message delegates to ChatHistoryCRUD."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_ai_message = AsyncMock()

            # Act
            await chat_history_adapter.add_ai_message("AI response")

            # Assert
            mock_crud.add_ai_message.assert_called_once_with(
                mock_db_session, sample_session_id, "AI response"
            )

    @pytest.mark.asyncio
    async def test_add_ai_message_should_propagate_session_validation_error(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test add_ai_message propagates ValueError from CRUD layer."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_ai_message = AsyncMock(
                side_effect=ValueError("Session not found")
            )

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_adapter.add_ai_message("Response")

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryAdapterGetMessages:
    """Test suite for ChatHistoryAdapter.get_messages() method."""

    @pytest.mark.asyncio
    async def test_get_messages_should_return_all_messages_when_no_limit(
        self,
        chat_history_adapter: ChatHistoryAdapter,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test get_messages returns all messages when limit is None."""
        # Arrange
        messages = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello"),
            HumanMessage(content="How are you?"),
        ]
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.get_messages = AsyncMock(return_value=messages)

            # Act
            result = await chat_history_adapter.get_messages(limit=None)

            # Assert
            assert result == messages
            assert len(result) == 3
            mock_crud.get_messages.assert_called_once_with(
                mock_db_session, sample_session_id
            )

    @pytest.mark.asyncio
    async def test_get_messages_should_return_recent_messages_with_limit(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages returns only most recent N messages when limit > 0."""
        # Arrange
        messages = [
            HumanMessage(content="Message 1"),
            AIMessage(content="Message 2"),
            HumanMessage(content="Message 3"),
            AIMessage(content="Message 4"),
            HumanMessage(content="Message 5"),
        ]
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.get_messages = AsyncMock(return_value=messages)

            # Act
            result = await chat_history_adapter.get_messages(limit=2)

            # Assert
            assert len(result) == 2
            assert result[0].content == "Message 4"
            assert result[1].content == "Message 5"

    @pytest.mark.asyncio
    async def test_get_messages_should_return_empty_list_when_no_messages(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages returns empty list when session has no messages."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.get_messages = AsyncMock(return_value=[])

            # Act
            result = await chat_history_adapter.get_messages(limit=None)

            # Assert
            assert result == []

    @pytest.mark.asyncio
    async def test_get_messages_should_return_empty_when_limit_exceeds_messages(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages returns all messages when limit > message count."""
        # Arrange
        messages = [HumanMessage(content="Single message")]
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.get_messages = AsyncMock(return_value=messages)

            # Act
            result = await chat_history_adapter.get_messages(limit=10)

            # Assert
            assert len(result) == 1
            assert result[0].content == "Single message"

    @pytest.mark.asyncio
    async def test_get_messages_should_ignore_zero_or_negative_limit(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages ignores zero or negative limit values."""
        # Arrange
        messages = [
            HumanMessage(content="Msg 1"),
            HumanMessage(content="Msg 2"),
        ]
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.get_messages = AsyncMock(return_value=messages)

            # Act - test with 0
            result = await chat_history_adapter.get_messages(limit=0)

            # Assert - should return all messages (0 is falsy)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_messages_should_propagate_session_validation_error(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages propagates ValueError from CRUD layer."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.get_messages = AsyncMock(
                side_effect=ValueError("Session not found")
            )

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_adapter.get_messages()

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryAdapterGetMessagesAsDicts:
    """Test suite for ChatHistoryAdapter.get_messages_as_dicts() method."""

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_convert_to_dict_format(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages_as_dicts converts messages to dict format."""
        # Arrange
        messages = [
            HumanMessage(content="What is AI?"),
            AIMessage(content="AI is artificial intelligence."),
        ]
        with patch.object(
            chat_history_adapter, "get_messages", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = messages

            # Act
            result = await chat_history_adapter.get_messages_as_dicts()

            # Assert
            assert len(result) == 2
            assert result[0]["role"] == "human"
            assert result[0]["content"] == "What is AI?"
            assert result[1]["role"] == "ai"
            assert result[1]["content"] == "AI is artificial intelligence."

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_include_role_and_content(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test each dict has 'role' and 'content' keys."""
        # Arrange
        messages = [HumanMessage(content="Hello")]
        with patch.object(
            chat_history_adapter, "get_messages", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = messages

            # Act
            result = await chat_history_adapter.get_messages_as_dicts()

            # Assert
            assert len(result) == 1
            assert "role" in result[0]
            assert "content" in result[0]
            assert len(result[0]) == 2

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_respect_limit_parameter(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages_as_dicts respects limit parameter."""
        # Arrange
        messages = [
            HumanMessage(content="Msg 1"),
            AIMessage(content="Msg 2"),
            HumanMessage(content="Msg 3"),
        ]
        with patch.object(
            chat_history_adapter, "get_messages", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = messages[-2:]  # Simulating limit=2

            # Act
            result = await chat_history_adapter.get_messages_as_dicts(limit=2)

            # Assert
            assert len(result) == 2
            # get_messages is called with positional limit argument
            mock_get.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_return_empty_list_when_no_messages(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages_as_dicts returns empty list when no messages exist."""
        # Arrange
        with patch.object(
            chat_history_adapter, "get_messages", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            # Act
            result = await chat_history_adapter.get_messages_as_dicts()

            # Assert
            assert result == []

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_preserve_content_exactly(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test message content is preserved exactly in dict format."""
        # Arrange
        content = "Multi-line content\nwith special chars: @#$%"
        messages = [HumanMessage(content=content)]
        with patch.object(
            chat_history_adapter, "get_messages", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = messages

            # Act
            result = await chat_history_adapter.get_messages_as_dicts()

            # Assert
            assert result[0]["content"] == content

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_propagate_session_error(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test get_messages_as_dicts propagates ValueError from underlying call."""
        # Arrange
        with patch.object(
            chat_history_adapter,
            "get_messages",
            new_callable=AsyncMock,
            side_effect=ValueError("Session not found"),
        ):
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_adapter.get_messages_as_dicts()

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryAdapterClear:
    """Test suite for ChatHistoryAdapter.clear() method."""

    @pytest.mark.asyncio
    async def test_clear_should_delegate_to_crud(
        self,
        chat_history_adapter: ChatHistoryAdapter,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test clear delegates to ChatHistoryCRUD.clear_history()."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.clear_history = AsyncMock()

            # Act
            await chat_history_adapter.clear()

            # Assert
            mock_crud.clear_history.assert_called_once_with(
                mock_db_session, sample_session_id
            )

    @pytest.mark.asyncio
    async def test_clear_should_propagate_session_validation_error(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test clear propagates ValueError from CRUD layer."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.clear_history = AsyncMock(
                side_effect=ValueError("Session not found")
            )

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_adapter.clear()

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryAdapterMessageTypes:
    """Test suite for message type handling in ChatHistoryAdapter."""

    @pytest.mark.asyncio
    async def test_add_message_with_human_messages(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test adapter handles HumanMessage type correctly."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_user_message = AsyncMock()

            # Act
            await chat_history_adapter.add_message("user", "Hello")

            # Assert - should call add_user_message without exception
            mock_crud.add_user_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_with_ai_messages(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test adapter handles AIMessage type correctly."""
        # Arrange
        with patch(
            "backend.application.adapters.chat_history_adapter.chat_history_crud"
        ) as mock_crud:
            mock_crud.add_ai_message = AsyncMock()

            # Act
            await chat_history_adapter.add_message("ai", "Hi there")

            # Assert - should call add_ai_message without exception
            mock_crud.add_ai_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_messages_as_dicts_should_use_message_type_attribute(
        self, chat_history_adapter: ChatHistoryAdapter
    ) -> None:
        """Test role mapping uses msg.type attribute correctly."""
        # Arrange
        human_msg = HumanMessage(content="User input")
        ai_msg = AIMessage(content="AI output")

        with patch.object(
            chat_history_adapter, "get_messages", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [human_msg, ai_msg]

            # Act
            result = await chat_history_adapter.get_messages_as_dicts()

            # Assert
            # HumanMessage.type should be "human"
            # AIMessage.type should be "ai"
            assert result[0]["role"] == human_msg.type
            assert result[1]["role"] == ai_msg.type
