"""
Test suite for DocumentService.

Tests document upload, processing, search, deletion, and retrieval.
Uses mocked dependencies (db, DevDocumentPipeline, CRUD operations).

System role: Verification of document service orchestration layer
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.services.document_service import DocumentService
from backend.boundary.db.models.document_model import DocumentStatus
from backend.boundary.vdb.dev_task import DevPipelineResult
from backend.core.exceptions import ParsingError


@pytest.fixture
def mock_db_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_session_id() -> uuid.UUID:
    """Provide sample session UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_document_id() -> uuid.UUID:
    """Provide sample document UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_dev_pipeline() -> MagicMock:
    """Provide mock DevDocumentPipeline."""
    return MagicMock()


@pytest.fixture
def sample_pipeline_result() -> DevPipelineResult:
    """Provide sample DevPipelineResult."""
    return DevPipelineResult(
        document_id="test-doc-1",
        session_id="test-session-1",
        num_chunks=5,
        processing_time_sec=1.23,
        total_tokens=1000,
    )


@pytest.fixture
def document_service(
    mock_db_session: AsyncSession, mock_dev_pipeline: MagicMock
) -> DocumentService:
    """Provide DocumentService instance with mocked pipeline."""
    return DocumentService(db=mock_db_session, dev_pipeline=mock_dev_pipeline)


class TestDocumentServiceInit:
    """Test suite for DocumentService initialization."""

    def test_init_should_store_db_and_pipeline(
        self, mock_db_session: AsyncSession, mock_dev_pipeline: MagicMock
    ) -> None:
        """Test DocumentService stores db and pipeline from constructor."""
        # Act
        service = DocumentService(db=mock_db_session, dev_pipeline=mock_dev_pipeline)

        # Assert
        assert service.db is mock_db_session
        assert service.pipeline is mock_dev_pipeline

    def test_init_should_create_default_pipeline_if_none(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test DocumentService creates DevDocumentPipeline if not provided."""
        # Act
        with patch(
            "backend.application.services.document_service.DevDocumentPipeline"
        ) as mock_pipeline_class:
            mock_pipeline_instance = MagicMock()
            mock_pipeline_class.return_value = mock_pipeline_instance

            service = DocumentService(db=mock_db_session, dev_pipeline=None)

            # Assert
            assert service.pipeline is mock_pipeline_instance


class TestDocumentServiceUploadDocument:
    """Test suite for DocumentService.upload_document method."""

    @pytest.mark.asyncio
    async def test_upload_document_should_validate_session_exists(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document raises ValueError when session doesn't exist."""
        # Arrange
        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="does not exist"):
                await document_service.upload_document(
                    file_path="/path/to/doc.pdf",
                    session_id=sample_session_id,
                    document_name="doc.pdf",
                )

    @pytest.mark.asyncio
    async def test_upload_document_should_create_document_record(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_pipeline_result: DevPipelineResult,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document creates document record in DB."""
        # Arrange
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = uuid.uuid4()

        document_service.pipeline.process.return_value = sample_pipeline_result

        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.document_service.document_crud.create",
            new_callable=AsyncMock,
            return_value=mock_document,
        ) as mock_create, patch(
            "backend.application.services.document_service.document_crud.update_status",
            new_callable=AsyncMock,
        ):
            # Act
            await document_service.upload_document(
                file_path="/path/to/doc.pdf",
                session_id=sample_session_id,
                document_name="doc.pdf",
            )

            # Assert
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs["name"] == "doc.pdf"
            assert call_args.kwargs["session_id"] == sample_session_id
            assert call_args.kwargs["upload_url"] == "/path/to/doc.pdf"
            assert call_args.kwargs["status"] == DocumentStatus.PENDING

    @pytest.mark.asyncio
    async def test_upload_document_should_process_through_pipeline(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_pipeline_result: DevPipelineResult,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document processes document through pipeline."""
        # Arrange
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = uuid.uuid4()

        document_service.pipeline.process.return_value = sample_pipeline_result

        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.document_service.document_crud.create",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.update_status",
            new_callable=AsyncMock,
        ):
            # Act
            await document_service.upload_document(
                file_path="/path/to/doc.pdf",
                session_id=sample_session_id,
                document_name="doc.pdf",
            )

            # Assert
            document_service.pipeline.process.assert_called_once()
            call_args = document_service.pipeline.process.call_args
            assert call_args.kwargs["file_path"] == "/path/to/doc.pdf"
            assert call_args.kwargs["document_id"] == str(mock_document.id)
            assert call_args.kwargs["session_id"] == str(sample_session_id)

    @pytest.mark.asyncio
    async def test_upload_document_should_update_status_to_completed(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_pipeline_result: DevPipelineResult,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document updates document status to COMPLETED."""
        # Arrange
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = uuid.uuid4()

        document_service.pipeline.process.return_value = sample_pipeline_result

        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.document_service.document_crud.create",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.update_status",
            new_callable=AsyncMock,
        ) as mock_update_status:
            # Act
            await document_service.upload_document(
                file_path="/path/to/doc.pdf",
                session_id=sample_session_id,
                document_name="doc.pdf",
            )

            # Assert
            mock_update_status.assert_called_once_with(
                mock_db_session,
                mock_document.id,
                DocumentStatus.COMPLETED,
            )

    @pytest.mark.asyncio
    async def test_upload_document_should_mark_failed_on_parsing_error(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document marks document FAILED on ParsingError."""
        # Arrange
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = uuid.uuid4()

        document_service.pipeline.process.side_effect = ParsingError(
            message="Parse failed", details={}
        )

        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.document_service.document_crud.create",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.mark_failed",
            new_callable=AsyncMock,
        ) as mock_mark_failed:
            # Act & Assert
            with pytest.raises(ParsingError):
                await document_service.upload_document(
                    file_path="/path/to/doc.pdf",
                    session_id=sample_session_id,
                    document_name="doc.pdf",
                )

            mock_mark_failed.assert_called_once()
            call_args = mock_mark_failed.call_args
            assert call_args.args[1] == mock_document.id

    @pytest.mark.asyncio
    async def test_upload_document_should_wrap_generic_exception_as_parsing_error(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document wraps generic exceptions as ParsingError."""
        # Arrange
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = uuid.uuid4()

        document_service.pipeline.process.side_effect = RuntimeError("Processing failed")

        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.document_service.document_crud.create",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.mark_failed",
            new_callable=AsyncMock,
        ):
            # Act & Assert
            with pytest.raises(
                ParsingError, match="Document processing failed"
            ) as exc_info:
                await document_service.upload_document(
                    file_path="/path/to/doc.pdf",
                    session_id=sample_session_id,
                    document_name="doc.pdf",
                )

            assert "Processing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_document_should_return_pipeline_result(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_pipeline_result: DevPipelineResult,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test upload_document returns pipeline processing result."""
        # Arrange
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = uuid.uuid4()

        document_service.pipeline.process.return_value = sample_pipeline_result

        with patch(
            "backend.application.services.document_service.session_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_session,
        ), patch(
            "backend.application.services.document_service.document_crud.create",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.update_status",
            new_callable=AsyncMock,
        ):
            # Act
            result = await document_service.upload_document(
                file_path="/path/to/doc.pdf",
                session_id=sample_session_id,
                document_name="doc.pdf",
            )

            # Assert
            assert result == sample_pipeline_result
            assert result.num_chunks == 5


class TestDocumentServiceSearchDocuments:
    """Test suite for DocumentService.search_documents method."""

    @pytest.mark.asyncio
    async def test_search_documents_should_call_pipeline_search(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test search_documents delegates to pipeline.search."""
        # Arrange
        expected_results = [
            {"content": "Result 1", "score": 0.95},
            {"content": "Result 2", "score": 0.87},
        ]
        document_service.pipeline.search.return_value = expected_results

        # Act
        result = await document_service.search_documents(
            query="test query",
            session_id=sample_session_id,
            k=5,
        )

        # Assert
        assert result == expected_results
        document_service.pipeline.search.assert_called_once_with(
            query="test query",
            k=5,
            session_id=str(sample_session_id),
            doc_id=None,
        )

    @pytest.mark.asyncio
    async def test_search_documents_should_filter_by_document_id(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_document_id: uuid.UUID,
    ) -> None:
        """Test search_documents filters by doc_id when provided."""
        # Arrange
        document_service.pipeline.search.return_value = []

        # Act
        await document_service.search_documents(
            query="test query",
            session_id=sample_session_id,
            k=3,
            doc_id=sample_document_id,
        )

        # Assert
        document_service.pipeline.search.assert_called_once_with(
            query="test query",
            k=3,
            session_id=str(sample_session_id),
            doc_id=str(sample_document_id),
        )


class TestDocumentServiceGetSessionDocuments:
    """Test suite for DocumentService.get_session_documents method."""

    @pytest.mark.asyncio
    async def test_get_session_documents_should_return_document_names(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test get_session_documents returns list of document names."""
        # Arrange
        mock_docs = [
            MagicMock(name="document1.pdf"),
            MagicMock(name="document2.pdf"),
            MagicMock(name="document3.pdf"),
        ]

        with patch(
            "backend.application.services.document_service.document_crud.get_by_session_id",
            new_callable=AsyncMock,
            return_value=mock_docs,
        ) as mock_get:
            # Act
            result = await document_service.get_session_documents(sample_session_id)

            # Assert
            assert result == ["document1.pdf", "document2.pdf", "document3.pdf"]
            mock_get.assert_called_once_with(mock_db_session, sample_session_id)

    @pytest.mark.asyncio
    async def test_get_session_documents_should_return_empty_list_for_no_documents(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test get_session_documents returns empty list when no documents exist."""
        # Arrange
        with patch(
            "backend.application.services.document_service.document_crud.get_by_session_id",
            new_callable=AsyncMock,
            return_value=[],
        ):
            # Act
            result = await document_service.get_session_documents(sample_session_id)

            # Assert
            assert result == []


class TestDocumentServiceDeleteDocument:
    """Test suite for DocumentService.delete_document method."""

    @pytest.mark.asyncio
    async def test_delete_document_should_validate_document_exists(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_document_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test delete_document raises ValueError when document doesn't exist."""
        # Arrange
        with patch(
            "backend.application.services.document_service.document_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="does not exist"):
                await document_service.delete_document(
                    doc_id=sample_document_id,
                    session_id=sample_session_id,
                )

    @pytest.mark.asyncio
    async def test_delete_document_should_validate_document_belongs_to_session(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_document_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test delete_document validates document belongs to session."""
        # Arrange
        other_session_id = uuid.uuid4()
        mock_document = MagicMock()
        mock_document.session_id = other_session_id

        with patch(
            "backend.application.services.document_service.document_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_document,
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="does not belong to session"):
                await document_service.delete_document(
                    doc_id=sample_document_id,
                    session_id=sample_session_id,
                )

    @pytest.mark.asyncio
    async def test_delete_document_should_delete_from_vector_store(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_document_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test delete_document deletes from vector store."""
        # Arrange
        mock_document = MagicMock()
        mock_document.session_id = sample_session_id
        mock_faiss_store = MagicMock()
        document_service.pipeline._faiss_store = mock_faiss_store

        with patch(
            "backend.application.services.document_service.document_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.delete_by_id",
            new_callable=AsyncMock,
        ):
            # Act
            await document_service.delete_document(
                doc_id=sample_document_id,
                session_id=sample_session_id,
            )

            # Assert
            mock_faiss_store.delete_by_doc_id.assert_called_once_with(
                str(sample_document_id)
            )

    @pytest.mark.asyncio
    async def test_delete_document_should_delete_from_database(
        self,
        document_service: DocumentService,
        sample_session_id: uuid.UUID,
        sample_document_id: uuid.UUID,
        mock_db_session: AsyncSession,
    ) -> None:
        """Test delete_document deletes document record from database."""
        # Arrange
        mock_document = MagicMock()
        mock_document.session_id = sample_session_id
        document_service.pipeline._faiss_store = MagicMock()

        with patch(
            "backend.application.services.document_service.document_crud.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_document,
        ), patch(
            "backend.application.services.document_service.document_crud.delete_by_id",
            new_callable=AsyncMock,
        ) as mock_delete:
            # Act
            await document_service.delete_document(
                doc_id=sample_document_id,
                session_id=sample_session_id,
            )

            # Assert
            mock_delete.assert_called_once_with(mock_db_session, sample_document_id)
