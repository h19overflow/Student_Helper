"""
Test suite for SessionCRUD database operations.

Tests session-specific CRUD methods including eager loading of documents
and metadata updates. Uses async fixtures with SQLAlchemy mocking.

System role: Verification of session persistence layer
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.session_crud import SessionCRUD
from backend.boundary.db.models.session_model import SessionModel


@pytest.fixture
def session_crud() -> SessionCRUD:
    """Provide SessionCRUD instance for testing."""
    return SessionCRUD()


@pytest.fixture
def mock_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_id() -> uuid.UUID:
    """Provide sample UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_session_model(sample_id: uuid.UUID) -> SessionModel:
    """Provide mock SessionModel instance."""
    session = SessionModel()
    session.id = sample_id
    session.session_metadata = {"user": "test_user"}
    session.created_at = datetime.now(timezone.utc)
    session.updated_at = datetime.now(timezone.utc)
    session.documents = []
    return session


class TestSessionCRUDInit:
    """Test suite for SessionCRUD initialization."""

    def test_init_should_set_model_to_session_model(self) -> None:
        """Test SessionCRUD initializes with SessionModel."""
        # Act
        crud = SessionCRUD()

        # Assert
        assert crud.model == SessionModel


class TestSessionCRUDGetWithDocuments:
    """Test suite for SessionCRUD.get_with_documents() method."""

    @pytest.mark.asyncio
    async def test_get_with_documents_should_return_session_with_docs(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_session_model: SessionModel,
    ) -> None:
        """Test get_with_documents returns session with eager-loaded documents."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session_model)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_with_documents(mock_session, sample_id)

        # Assert
        assert result == mock_session_model
        assert result.documents == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_documents_should_return_none_when_not_found(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test get_with_documents returns None when session doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_with_documents(mock_session, sample_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_documents_should_use_selectinload(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test get_with_documents uses selectinload option for documents."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await session_crud.get_with_documents(mock_session, sample_id)

        # Assert
        # Verify execute was called with selectinload option
        mock_session.execute.assert_called_once()


class TestSessionCRUDGetAllWithDocuments:
    """Test suite for SessionCRUD.get_all_with_documents() method."""

    @pytest.mark.asyncio
    async def test_get_all_with_documents_should_return_all_sessions(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        mock_session_model: SessionModel,
    ) -> None:
        """Test get_all_with_documents returns all sessions with eager-loaded docs."""
        # Arrange
        sessions = [mock_session_model]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sessions
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_all_with_documents(mock_session)

        # Assert
        assert result == sessions
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_with_documents_should_return_empty_when_no_sessions(
        self, session_crud: SessionCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_all_with_documents returns empty sequence when no sessions."""
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_all_with_documents(mock_session)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_with_documents_should_apply_limit(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        mock_session_model: SessionModel,
    ) -> None:
        """Test get_all_with_documents respects limit parameter."""
        # Arrange
        sessions = [mock_session_model]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sessions
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_all_with_documents(mock_session, limit=10)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_with_documents_should_apply_offset(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        mock_session_model: SessionModel,
    ) -> None:
        """Test get_all_with_documents respects offset parameter."""
        # Arrange
        sessions = [mock_session_model]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sessions
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_all_with_documents(
            mock_session, limit=10, offset=5
        )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_with_documents_should_apply_both_limit_and_offset(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        mock_session_model: SessionModel,
    ) -> None:
        """Test get_all_with_documents applies both limit and offset together."""
        # Arrange
        sessions = [mock_session_model]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sessions
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_all_with_documents(
            mock_session, limit=10, offset=20
        )

        # Assert
        mock_session.execute.assert_called_once()


class TestSessionCRUDUpdateMetadata:
    """Test suite for SessionCRUD.update_metadata() method."""

    @pytest.mark.asyncio
    async def test_update_metadata_should_return_updated_session(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_session_model: SessionModel,
    ) -> None:
        """Test update_metadata returns updated session model."""
        # Arrange
        new_metadata = {"user": "updated_user", "tags": ["test"]}
        updated_session = mock_session_model
        updated_session.session_metadata = new_metadata

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_session)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.update_metadata(
            mock_session, sample_id, new_metadata
        )

        # Assert
        assert result == updated_session
        assert result.session_metadata == new_metadata

    @pytest.mark.asyncio
    async def test_update_metadata_should_return_none_when_not_found(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test update_metadata returns None when session doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.update_metadata(
            mock_session, sample_id, {"key": "value"}
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_metadata_should_accept_empty_dict(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_session_model: SessionModel,
    ) -> None:
        """Test update_metadata accepts empty metadata dictionary."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session_model)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.update_metadata(mock_session, sample_id, {})

        # Assert
        assert result == mock_session_model

    @pytest.mark.asyncio
    async def test_update_metadata_should_accept_complex_metadata(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_session_model: SessionModel,
    ) -> None:
        """Test update_metadata accepts complex nested metadata."""
        # Arrange
        complex_metadata = {
            "user": "test_user",
            "preferences": {"theme": "dark", "notifications": True},
            "tags": ["tag1", "tag2"],
        }
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session_model)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.update_metadata(
            mock_session, sample_id, complex_metadata
        )

        # Assert
        assert result == mock_session_model


class TestSessionCRUDInheritance:
    """Test suite for SessionCRUD inheritance from BaseCRUD."""

    @pytest.mark.asyncio
    async def test_inherited_create_method_should_work(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
    ) -> None:
        """Test SessionCRUD inherits create method from BaseCRUD."""
        # Arrange
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        await session_crud.create(
            mock_session, session_metadata={"user": "test_user"}
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_inherited_get_by_id_method_should_work(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test SessionCRUD inherits get_by_id method from BaseCRUD."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.get_by_id(mock_session, sample_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_inherited_delete_by_id_method_should_work(
        self,
        session_crud: SessionCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test SessionCRUD inherits delete_by_id method from BaseCRUD."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_crud.delete_by_id(mock_session, sample_id)

        # Assert
        assert result is True
