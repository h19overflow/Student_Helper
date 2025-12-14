"""
Test suite for dependency injection container.

Tests factory functions for service creation and configuration.
Verifies ChatService, DocumentService, and RAGAgent initialization.

System role: Verification of DI container
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    get_chat_service,
    get_document_service,
    get_job_service,
    get_session_service,
    get_diagram_service,
    get_settings_dependency,
)
from backend.application.services import (
    ChatService,
    DocumentService,
    JobService,
    SessionService,
    DiagramService,
)
from backend.core.agentic_system.agent.rag_agent import RAGAgent


@pytest.fixture
def mock_db_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


class TestGetChatService:
    """Test suite for get_chat_service factory."""

    def test_get_chat_service_should_return_chat_service_instance(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_chat_service returns ChatService instance."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session), patch(
            "backend.api.deps.dependencies.FAISSStore"
        ), patch("backend.api.deps.dependencies.RAGAgent"):
            # Act
            service = get_chat_service(db=mock_db_session)

            # Assert
            assert isinstance(service, ChatService)

    def test_get_chat_service_should_initialize_with_db_and_rag_agent(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_chat_service initializes ChatService with db and RAGAgent."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session), patch(
            "backend.api.deps.dependencies.FAISSStore"
        ) as mock_faiss_class, patch(
            "backend.api.deps.dependencies.RAGAgent"
        ) as mock_rag_agent_class:
            mock_faiss_instance = MagicMock()
            mock_faiss_class.return_value = mock_faiss_instance

            mock_rag_agent_instance = MagicMock()
            mock_rag_agent_class.return_value = mock_rag_agent_instance

            # Act
            service = get_chat_service(db=mock_db_session)

            # Assert
            assert service.db is mock_db_session
            assert service.rag_agent is mock_rag_agent_instance

    def test_get_chat_service_should_create_faiss_store(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_chat_service creates FAISSStore with correct params."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session), patch(
            "backend.api.deps.dependencies.FAISSStore"
        ) as mock_faiss_class, patch(
            "backend.api.deps.dependencies.RAGAgent"
        ):
            mock_faiss_instance = MagicMock()
            mock_faiss_class.return_value = mock_faiss_instance

            # Act
            get_chat_service(db=mock_db_session)

            # Assert
            mock_faiss_class.assert_called_once()
            call_kwargs = mock_faiss_class.call_args.kwargs
            assert "persist_directory" in call_kwargs
            assert "model_id" in call_kwargs
            assert "region" in call_kwargs

    def test_get_chat_service_should_create_rag_agent(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_chat_service creates RAGAgent with correct params."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session), patch(
            "backend.api.deps.dependencies.FAISSStore"
        ) as mock_faiss_class, patch(
            "backend.api.deps.dependencies.RAGAgent"
        ) as mock_rag_agent_class:
            mock_faiss_instance = MagicMock()
            mock_faiss_class.return_value = mock_faiss_instance

            # Act
            get_chat_service(db=mock_db_session)

            # Assert
            mock_rag_agent_class.assert_called_once()
            call_kwargs = mock_rag_agent_class.call_args.kwargs
            assert call_kwargs["vector_store"] is mock_faiss_instance
            assert "model_id" in call_kwargs
            assert "region" in call_kwargs
            assert "temperature" in call_kwargs


class TestGetDocumentService:
    """Test suite for get_document_service factory."""

    def test_get_document_service_should_return_document_service_instance(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_document_service returns DocumentService instance."""
        # Arrange
        with patch(
            "backend.api.deps.dependencies.get_db", return_value=mock_db_session
        ), patch("backend.api.deps.dependencies.DevDocumentPipeline"):
            # Act
            service = get_document_service(db=mock_db_session)

            # Assert
            assert isinstance(service, DocumentService)

    def test_get_document_service_should_initialize_with_pipeline(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_document_service initializes with DevDocumentPipeline."""
        # Arrange
        with patch(
            "backend.api.deps.dependencies.get_db", return_value=mock_db_session
        ), patch("backend.api.deps.dependencies.DevDocumentPipeline") as mock_pipeline_class:
            mock_pipeline_instance = MagicMock()
            mock_pipeline_class.return_value = mock_pipeline_instance

            # Act
            service = get_document_service(db=mock_db_session)

            # Assert
            assert service.pipeline is mock_pipeline_instance

    def test_get_document_service_should_create_pipeline_with_correct_params(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_document_service creates pipeline with correct params."""
        # Arrange
        with patch(
            "backend.api.deps.dependencies.get_db", return_value=mock_db_session
        ), patch(
            "backend.api.deps.dependencies.DevDocumentPipeline"
        ) as mock_pipeline_class:
            # Act
            get_document_service(db=mock_db_session)

            # Assert
            mock_pipeline_class.assert_called_once()
            call_kwargs = mock_pipeline_class.call_args.kwargs
            assert "chunk_size" in call_kwargs
            assert "chunk_overlap" in call_kwargs
            assert "persist_directory" in call_kwargs


class TestGetJobService:
    """Test suite for get_job_service factory."""

    def test_get_job_service_should_return_job_service_instance(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_job_service returns JobService instance."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session):
            # Act
            service = get_job_service(db=mock_db_session)

            # Assert
            assert isinstance(service, JobService)

    def test_get_job_service_should_initialize_with_db(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_job_service initializes with database session."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session):
            # Act
            service = get_job_service(db=mock_db_session)

            # Assert
            assert service.db is mock_db_session


class TestGetSessionService:
    """Test suite for get_session_service factory."""

    def test_get_session_service_should_return_session_service_instance(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_session_service returns SessionService instance."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session):
            # Act
            service = get_session_service(db=mock_db_session)

            # Assert
            assert isinstance(service, SessionService)

    def test_get_session_service_should_initialize_with_db(
        self, mock_db_session: AsyncSession
    ) -> None:
        """Test get_session_service initializes with database session."""
        # Arrange
        with patch("backend.api.deps.dependencies.get_db", return_value=mock_db_session):
            # Act
            service = get_session_service(db=mock_db_session)

            # Assert
            assert service.db is mock_db_session


class TestGetDiagramService:
    """Test suite for get_diagram_service factory."""

    def test_get_diagram_service_should_return_diagram_service_instance(
        self,
    ) -> None:
        """Test get_diagram_service returns DiagramService instance."""
        # Act
        service = get_diagram_service()

        # Assert
        assert isinstance(service, DiagramService)


class TestGetSettingsDependency:
    """Test suite for get_settings_dependency factory."""

    def test_get_settings_dependency_should_return_settings(self) -> None:
        """Test get_settings_dependency returns Settings instance."""
        # Act
        settings = get_settings_dependency()

        # Assert
        assert settings is not None

    def test_get_settings_dependency_should_be_cached(self) -> None:
        """Test get_settings_dependency returns cached instance."""
        # Act
        settings1 = get_settings_dependency()
        settings2 = get_settings_dependency()

        # Assert
        assert settings1 is settings2  # Same object (cached)
