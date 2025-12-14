"""
Test suite for DocumentCRUD database operations.

Tests document-specific CRUD methods including filtering by session, status,
and status update operations. Uses async fixtures with SQLAlchemy mocking.

System role: Verification of document persistence layer
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.document_crud import DocumentCRUD
from backend.boundary.db.models.document_model import DocumentModel, DocumentStatus


@pytest.fixture
def document_crud() -> DocumentCRUD:
    """Provide DocumentCRUD instance for testing."""
    return DocumentCRUD()


@pytest.fixture
def mock_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_id() -> uuid.UUID:
    """Provide sample UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_session_id() -> uuid.UUID:
    """Provide sample session UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_document_model(sample_id: uuid.UUID, sample_session_id: uuid.UUID) -> DocumentModel:
    """Provide mock DocumentModel instance."""
    doc = DocumentModel()
    doc.id = sample_id
    doc.session_id = sample_session_id
    doc.name = "test_document.pdf"
    doc.status = DocumentStatus.PENDING
    doc.upload_url = "s3://bucket/test_document.pdf"
    doc.error_message = None
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


class TestDocumentCRUDInit:
    """Test suite for DocumentCRUD initialization."""

    def test_init_should_set_model_to_document_model(self) -> None:
        """Test DocumentCRUD initializes with DocumentModel."""
        # Act
        crud = DocumentCRUD()

        # Assert
        assert crud.model == DocumentModel


class TestDocumentCRUDGetBySessionID:
    """Test suite for DocumentCRUD.get_by_session_id() method."""

    @pytest.mark.asyncio
    async def test_get_by_session_id_should_return_documents_for_session(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_session_id: uuid.UUID,
        mock_document_model: DocumentModel,
    ) -> None:
        """Test get_by_session_id returns all documents for a session."""
        # Arrange
        documents = [mock_document_model]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=documents)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.get_by_session_id(mock_session, sample_session_id)

        # Assert
        assert result == documents
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_session_id_should_return_empty_when_no_documents(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test get_by_session_id returns empty sequence when session has no docs."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.get_by_session_id(mock_session, sample_session_id)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_session_id_should_apply_limit(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_session_id: uuid.UUID,
        mock_document_model: DocumentModel,
    ) -> None:
        """Test get_by_session_id respects limit parameter."""
        # Arrange
        documents = [mock_document_model]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=documents)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.get_by_session_id(
            mock_session, sample_session_id, limit=5
        )

        # Assert
        assert len(result) == 1


class TestDocumentCRUDGetByStatus:
    """Test suite for DocumentCRUD.get_by_status() method."""

    @pytest.mark.asyncio
    async def test_get_by_status_should_return_documents_with_status(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        mock_document_model: DocumentModel,
    ) -> None:
        """Test get_by_status returns documents with specific status."""
        # Arrange
        documents = [mock_document_model]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=documents)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.get_by_status(
            mock_session, DocumentStatus.PENDING
        )

        # Assert
        assert result == documents
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_status_should_return_empty_when_no_documents(
        self, document_crud: DocumentCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_by_status returns empty when no documents match status."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.get_by_status(
            mock_session, DocumentStatus.COMPLETED
        )

        # Assert
        assert result == []


class TestDocumentCRUDUpdateStatus:
    """Test suite for DocumentCRUD.update_status() method."""

    @pytest.mark.asyncio
    async def test_update_status_should_return_updated_document(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_document_model: DocumentModel,
    ) -> None:
        """Test update_status returns updated document model."""
        # Arrange
        updated_doc = mock_document_model
        updated_doc.status = DocumentStatus.PROCESSING

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_doc)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.update_status(
            mock_session, sample_id, DocumentStatus.PROCESSING
        )

        # Assert
        assert result == updated_doc
        assert result.status == DocumentStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_status_should_return_none_when_not_found(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test update_status returns None when document doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.update_status(
            mock_session, sample_id, DocumentStatus.PROCESSING
        )

        # Assert
        assert result is None


class TestDocumentCRUDMarkCompleted:
    """Test suite for DocumentCRUD.mark_completed() method."""

    @pytest.mark.asyncio
    async def test_mark_completed_should_set_status_to_completed(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_document_model: DocumentModel,
    ) -> None:
        """Test mark_completed sets status to COMPLETED."""
        # Arrange
        updated_doc = mock_document_model
        updated_doc.status = DocumentStatus.COMPLETED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_doc)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.mark_completed(mock_session, sample_id)

        # Assert
        assert result == updated_doc
        assert result.status == DocumentStatus.COMPLETED


class TestDocumentCRUDMarkFailed:
    """Test suite for DocumentCRUD.mark_failed() method."""

    @pytest.mark.asyncio
    async def test_mark_failed_should_set_status_and_error_message(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_document_model: DocumentModel,
    ) -> None:
        """Test mark_failed sets status to FAILED and includes error message."""
        # Arrange
        error_msg = "File corrupted"
        updated_doc = mock_document_model
        updated_doc.status = DocumentStatus.FAILED
        updated_doc.error_message = error_msg

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_doc)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.mark_failed(mock_session, sample_id, error_msg)

        # Assert
        assert result == updated_doc
        assert result.status == DocumentStatus.FAILED
        assert result.error_message == error_msg


class TestDocumentCRUDInheritance:
    """Test suite for DocumentCRUD inheritance from BaseCRUD."""

    @pytest.mark.asyncio
    async def test_inherited_get_by_id_method_should_work(
        self,
        document_crud: DocumentCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test DocumentCRUD inherits get_by_id method from BaseCRUD."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await document_crud.get_by_id(mock_session, sample_id)

        # Assert
        assert result is None
