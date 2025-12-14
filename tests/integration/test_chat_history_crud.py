"""
Test suite for ChatHistoryCRUD database operations.

Tests chat message persistence including adding user/AI messages, retrieving
messages, clearing history, and session validation. Uses async fixtures with
mocked PostgresChatMessageHistory to avoid database dependencies.

System role: Verification of chat history persistence layer
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.chat_history_crud import ChatHistoryCRUD


@pytest.fixture
def chat_history_crud() -> ChatHistoryCRUD:
    """Provide ChatHistoryCRUD instance for testing."""
    return ChatHistoryCRUD()


@pytest.fixture
def mock_db_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_session_id() -> uuid.UUID:
    """Provide sample session UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_chat_history():
    """Provide mock PostgresChatMessageHistory instance."""
    return MagicMock()


class TestChatHistoryCRUDInit:
    """Test suite for ChatHistoryCRUD initialization."""

    def test_init_should_set_connection_string(self) -> None:
        """Test ChatHistoryCRUD initializes with database connection string."""
        # Act
        crud = ChatHistoryCRUD()

        # Assert
        assert crud.connection_string is not None
        assert isinstance(crud.connection_string, str)
        assert "postgres" in crud.connection_string.lower()

    def test_table_name_should_be_chat_messages(self) -> None:
        """Test ChatHistoryCRUD has correct table name constant."""
        # Assert
        assert ChatHistoryCRUD.TABLE_NAME == "chat_messages"


class TestChatHistoryCRUDValidateSessionExists:
    """Test suite for ChatHistoryCRUD._validate_session_exists() method."""

    @pytest.mark.asyncio
    async def test_validate_session_exists_should_succeed_when_session_found(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test validation succeeds when session exists in database."""
        # Arrange
        mock_session_model = MagicMock()
        with patch(
            "backend.boundary.db.CRUD.chat_history_crud.session_crud"
        ) as mock_session_crud:
            mock_session_crud.get_by_id = AsyncMock(
                return_value=mock_session_model
            )

            # Act & Assert - should not raise
            await chat_history_crud._validate_session_exists(
                mock_db_session, sample_session_id
            )
            mock_session_crud.get_by_id.assert_called_once_with(
                mock_db_session, sample_session_id
            )

    @pytest.mark.asyncio
    async def test_validate_session_exists_should_raise_when_session_not_found(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test validation raises ValueError when session doesn't exist."""
        # Arrange
        with patch(
            "backend.boundary.db.CRUD.chat_history_crud.session_crud"
        ) as mock_session_crud:
            mock_session_crud.get_by_id = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_crud._validate_session_exists(
                    mock_db_session, sample_session_id
                )

            assert str(sample_session_id) in str(exc_info.value)
            assert "does not exist" in str(exc_info.value)


class TestChatHistoryCRUDGetChatHistory:
    """Test suite for ChatHistoryCRUD._get_chat_history() method."""

    def test_get_chat_history_should_create_postgres_chat_history(
        self,
        chat_history_crud: ChatHistoryCRUD,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test _get_chat_history creates PostgresChatMessageHistory with correct params."""
        # Arrange
        with patch(
            "backend.boundary.db.CRUD.chat_history_crud.PostgresChatMessageHistory"
        ) as mock_pgcmh_class:
            with patch(
                "backend.boundary.db.CRUD.chat_history_crud.psycopg.connect"
            ) as mock_connect:
                mock_connect.return_value = MagicMock()

                # Act
                chat_history_crud._get_chat_history(sample_session_id)

                # Assert
                mock_pgcmh_class.assert_called_once()
                call_kwargs = mock_pgcmh_class.call_args[1]
                assert call_kwargs["table_name"] == "chat_messages"
                assert call_kwargs["session_id"] == str(sample_session_id)
                assert "sync_connection" in call_kwargs

    def test_get_chat_history_should_use_correct_session_id_format(
        self,
        chat_history_crud: ChatHistoryCRUD,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test _get_chat_history converts session_id to string."""
        # Arrange
        with patch(
            "backend.boundary.db.CRUD.chat_history_crud.PostgresChatMessageHistory"
        ) as mock_pgcmh_class:
            with patch(
                "backend.boundary.db.CRUD.chat_history_crud.psycopg.connect"
            ):
                # Act
                chat_history_crud._get_chat_history(sample_session_id)

                # Assert
                call_kwargs = mock_pgcmh_class.call_args[1]
                assert call_kwargs["session_id"] == str(sample_session_id)
                assert isinstance(call_kwargs["session_id"], str)


class TestChatHistoryCRUDAddUserMessage:
    """Test suite for ChatHistoryCRUD.add_user_message() method."""

    @pytest.mark.asyncio
    async def test_add_user_message_should_validate_session_exists(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test add_user_message validates session before adding."""
        # Arrange
        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ) as mock_validate:
            with patch.object(
                chat_history_crud, "_get_chat_history"
            ) as mock_get_history:
                mock_get_history.return_value = MagicMock()

                # Act
                await chat_history_crud.add_user_message(
                    mock_db_session, sample_session_id, "Test message"
                )

                # Assert
                mock_validate.assert_called_once_with(
                    mock_db_session, sample_session_id
                )

    @pytest.mark.asyncio
    async def test_add_user_message_should_add_human_message(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test add_user_message creates HumanMessage and adds it."""
        # Arrange
        message_content = "What is Python?"
        mock_history = MagicMock()

        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ):
            with patch.object(
                chat_history_crud, "_get_chat_history", return_value=mock_history
            ):
                # Act
                await chat_history_crud.add_user_message(
                    mock_db_session, sample_session_id, message_content
                )

                # Assert
                mock_history.add_messages.assert_called_once()
                messages = mock_history.add_messages.call_args[0][0]
                assert len(messages) == 1
                assert isinstance(messages[0], HumanMessage)
                assert messages[0].content == message_content

    @pytest.mark.asyncio
    async def test_add_user_message_should_raise_when_session_invalid(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test add_user_message raises ValueError for invalid session."""
        # Arrange
        with patch.object(
            chat_history_crud,
            "_validate_session_exists",
            new_callable=AsyncMock,
            side_effect=ValueError("Session not found"),
        ):
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_crud.add_user_message(
                    mock_db_session, sample_session_id, "Test"
                )

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryCRUDAddAIMessage:
    """Test suite for ChatHistoryCRUD.add_ai_message() method."""

    @pytest.mark.asyncio
    async def test_add_ai_message_should_validate_session_exists(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test add_ai_message validates session before adding."""
        # Arrange
        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ) as mock_validate:
            with patch.object(
                chat_history_crud, "_get_chat_history"
            ) as mock_get_history:
                mock_get_history.return_value = MagicMock()

                # Act
                await chat_history_crud.add_ai_message(
                    mock_db_session, sample_session_id, "Test response"
                )

                # Assert
                mock_validate.assert_called_once_with(
                    mock_db_session, sample_session_id
                )

    @pytest.mark.asyncio
    async def test_add_ai_message_should_add_ai_message(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test add_ai_message creates AIMessage and adds it."""
        # Arrange
        message_content = "Python is a high-level programming language."
        mock_history = MagicMock()

        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ):
            with patch.object(
                chat_history_crud, "_get_chat_history", return_value=mock_history
            ):
                # Act
                await chat_history_crud.add_ai_message(
                    mock_db_session, sample_session_id, message_content
                )

                # Assert
                mock_history.add_messages.assert_called_once()
                messages = mock_history.add_messages.call_args[0][0]
                assert len(messages) == 1
                assert isinstance(messages[0], AIMessage)
                assert messages[0].content == message_content

    @pytest.mark.asyncio
    async def test_add_ai_message_should_raise_when_session_invalid(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test add_ai_message raises ValueError for invalid session."""
        # Arrange
        with patch.object(
            chat_history_crud,
            "_validate_session_exists",
            new_callable=AsyncMock,
            side_effect=ValueError("Session not found"),
        ):
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_crud.add_ai_message(
                    mock_db_session, sample_session_id, "Response"
                )

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryCRUDGetMessages:
    """Test suite for ChatHistoryCRUD.get_messages() method."""

    @pytest.mark.asyncio
    async def test_get_messages_should_validate_session_exists(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test get_messages validates session before retrieval."""
        # Arrange
        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ) as mock_validate:
            with patch.object(
                chat_history_crud, "_get_chat_history"
            ) as mock_get_history:
                mock_history = MagicMock()
                mock_history.messages = []
                mock_get_history.return_value = mock_history

                # Act
                await chat_history_crud.get_messages(
                    mock_db_session, sample_session_id
                )

                # Assert
                mock_validate.assert_called_once_with(
                    mock_db_session, sample_session_id
                )

    @pytest.mark.asyncio
    async def test_get_messages_should_return_messages_list(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test get_messages returns list of BaseMessage objects."""
        # Arrange
        messages = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello"),
            HumanMessage(content="How are you?"),
        ]
        mock_history = MagicMock()
        mock_history.messages = messages

        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ):
            with patch.object(
                chat_history_crud, "_get_chat_history", return_value=mock_history
            ):
                # Act
                result = await chat_history_crud.get_messages(
                    mock_db_session, sample_session_id
                )

                # Assert
                assert result == messages
                assert len(result) == 3
                assert all(isinstance(msg, BaseMessage) for msg in result)

    @pytest.mark.asyncio
    async def test_get_messages_should_return_empty_list_when_no_messages(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test get_messages returns empty list when session has no messages."""
        # Arrange
        mock_history = MagicMock()
        mock_history.messages = []

        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ):
            with patch.object(
                chat_history_crud, "_get_chat_history", return_value=mock_history
            ):
                # Act
                result = await chat_history_crud.get_messages(
                    mock_db_session, sample_session_id
                )

                # Assert
                assert result == []

    @pytest.mark.asyncio
    async def test_get_messages_should_raise_when_session_invalid(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test get_messages raises ValueError for invalid session."""
        # Arrange
        with patch.object(
            chat_history_crud,
            "_validate_session_exists",
            new_callable=AsyncMock,
            side_effect=ValueError("Session not found"),
        ):
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_crud.get_messages(
                    mock_db_session, sample_session_id
                )

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryCRUDClearHistory:
    """Test suite for ChatHistoryCRUD.clear_history() method."""

    @pytest.mark.asyncio
    async def test_clear_history_should_validate_session_exists(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test clear_history validates session before clearing."""
        # Arrange
        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ) as mock_validate:
            with patch.object(
                chat_history_crud, "_get_chat_history"
            ) as mock_get_history:
                mock_get_history.return_value = MagicMock()

                # Act
                await chat_history_crud.clear_history(
                    mock_db_session, sample_session_id
                )

                # Assert
                mock_validate.assert_called_once_with(
                    mock_db_session, sample_session_id
                )

    @pytest.mark.asyncio
    async def test_clear_history_should_call_clear_on_chat_history(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test clear_history calls clear() on PostgresChatMessageHistory."""
        # Arrange
        mock_history = MagicMock()

        with patch.object(
            chat_history_crud, "_validate_session_exists", new_callable=AsyncMock
        ):
            with patch.object(
                chat_history_crud, "_get_chat_history", return_value=mock_history
            ):
                # Act
                await chat_history_crud.clear_history(
                    mock_db_session, sample_session_id
                )

                # Assert
                mock_history.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_history_should_raise_when_session_invalid(
        self,
        chat_history_crud: ChatHistoryCRUD,
        mock_db_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test clear_history raises ValueError for invalid session."""
        # Arrange
        with patch.object(
            chat_history_crud,
            "_validate_session_exists",
            new_callable=AsyncMock,
            side_effect=ValueError("Session not found"),
        ):
            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await chat_history_crud.clear_history(
                    mock_db_session, sample_session_id
                )

            assert "Session not found" in str(exc_info.value)


class TestChatHistoryCRUDCreateTable:
    """Test suite for ChatHistoryCRUD.create_table() class method."""

    def test_create_table_should_call_postgres_chat_message_history_create_tables(
        self,
    ) -> None:
        """Test create_table calls PostgresChatMessageHistory.create_tables()."""
        # Arrange
        with patch(
            "backend.boundary.db.CRUD.chat_history_crud.psycopg.connect"
        ) as mock_connect:
            with patch(
                "backend.boundary.db.CRUD.chat_history_crud.PostgresChatMessageHistory.create_tables"
            ) as mock_create:
                mock_connection = MagicMock()
                mock_connect.return_value.__enter__ = MagicMock(
                    return_value=mock_connection
                )
                mock_connect.return_value.__exit__ = MagicMock(return_value=None)

                # Act
                ChatHistoryCRUD.create_table()

                # Assert
                mock_connect.assert_called_once()
                mock_create.assert_called_once_with(
                    mock_connection, ChatHistoryCRUD.TABLE_NAME
                )

    def test_create_table_should_use_correct_table_name(self) -> None:
        """Test create_table uses 'chat_messages' as table name."""
        # Arrange
        with patch(
            "backend.boundary.db.CRUD.chat_history_crud.psycopg.connect"
        ) as mock_connect:
            with patch(
                "backend.boundary.db.CRUD.chat_history_crud.PostgresChatMessageHistory.create_tables"
            ) as mock_create:
                mock_connection = MagicMock()
                mock_connect.return_value.__enter__ = MagicMock(
                    return_value=mock_connection
                )
                mock_connect.return_value.__exit__ = MagicMock(return_value=None)

                # Act
                ChatHistoryCRUD.create_table()

                # Assert
                call_args = mock_create.call_args[0]
                assert call_args[1] == "chat_messages"
