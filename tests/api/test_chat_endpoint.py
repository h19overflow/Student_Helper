"""
Test suite for chat API endpoint.

Tests POST /{session_id}/chat endpoint with FastAPI TestClient.
Covers successful chat requests, error handling, diagram generation, and citation mapping.

System role: Verification of chat HTTP API endpoint
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routers.sessions import router
from backend.core.agentic_system.agent.rag_agent_schema import (
    RAGResponse,
    RAGCitation,
)
from backend.models.chat import ChatRequest


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test application with chat router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_session_id() -> uuid.UUID:
    """Provide sample session UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_chat_request() -> ChatRequest:
    """Provide sample chat request."""
    return ChatRequest(
        message="What is the capital of France?",
        include_diagram=False,
    )


@pytest.fixture
def sample_rag_response() -> RAGResponse:
    """Provide sample RAG response with citations."""
    return RAGResponse(
        answer="The capital of France is Paris.",
        citations=[
            RAGCitation(
                chunk_id="chunk_001",
                content_snippet="Paris is the capital city of France",
                page=5,
                section="Geography",
                source_uri="s3://bucket/geography.pdf",
                relevance_score=0.98,
            ),
            RAGCitation(
                chunk_id="chunk_002",
                content_snippet="Paris, also known as the City of Light",
                page=10,
                section="History",
                source_uri="s3://bucket/history.pdf",
                relevance_score=0.92,
            ),
        ],
        confidence=0.95,
        reasoning="Both documents confirm Paris as the capital city.",
    )


class TestChatEndpointSuccessful:
    """Test suite for successful chat endpoint requests."""

    def test_chat_should_accept_valid_request(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_chat_request: ChatRequest,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint accepts valid chat request."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_get_diagram.return_value = mock_diagram_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": sample_chat_request.message,
                    "include_diagram": False,
                },
            )

            # Assert
            assert response.status_code == 200

    def test_chat_should_return_answer_and_citations(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_chat_request: ChatRequest,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint returns answer and citations."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_get_diagram.return_value = mock_diagram_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": sample_chat_request.message,
                    "include_diagram": False,
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == sample_rag_response.answer
            assert len(data["citations"]) == 2

    def test_chat_should_map_rag_citations_to_api_citations(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_chat_request: ChatRequest,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint maps RAGCitation to API Citation format."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_get_diagram.return_value = mock_diagram_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": sample_chat_request.message,
                    "include_diagram": False,
                },
            )

            # Assert
            data = response.json()
            citations = data["citations"]

            # First citation
            assert citations[0]["chunk_id"] == "chunk_001"
            assert citations[0]["page"] == 5
            assert citations[0]["section"] == "Geography"
            assert citations[0]["source_uri"] == "s3://bucket/geography.pdf"
            assert citations[0]["doc_name"] == "geography.pdf"  # Extracted from URI

            # Second citation
            assert citations[1]["chunk_id"] == "chunk_002"
            assert citations[1]["page"] == 10
            assert citations[1]["section"] == "History"

    def test_chat_should_extract_filename_from_source_uri(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint extracts filename from source URI for doc_name."""
        # Arrange
        rag_response = RAGResponse(
            answer="Test answer",
            citations=[
                RAGCitation(
                    chunk_id="chunk_1",
                    content_snippet="Snippet",
                    page=1,
                    section="Intro",
                    source_uri="s3://my-bucket/documents/my_document.pdf",
                    relevance_score=0.9,
                )
            ],
        )

        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_get_diagram.return_value = mock_diagram_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={"message": "Test", "include_diagram": False},
            )

            # Assert
            data = response.json()
            assert data["citations"][0]["doc_name"] == "my_document.pdf"


class TestChatEndpointDiagramGeneration:
    """Test suite for diagram generation in chat endpoint."""

    def test_chat_should_generate_diagram_when_requested(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint generates diagram when include_diagram is True."""
        # Arrange
        diagram_code = "graph TD; A-->B;"

        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_diagram_service.generate_diagram.return_value = {
                "diagram_code": diagram_code
            }
            mock_get_diagram.return_value = mock_diagram_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": "Show diagram",
                    "include_diagram": True,
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["mermaid_diagram"] == diagram_code
            mock_diagram_service.generate_diagram.assert_called_once()

    def test_chat_should_not_generate_diagram_when_not_requested(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint skips diagram generation when not requested."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_get_diagram.return_value = mock_diagram_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": "Test",
                    "include_diagram": False,
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["mermaid_diagram"] is None
            mock_diagram_service.generate_diagram.assert_not_called()

    def test_chat_should_pass_correct_params_to_diagram_service(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint passes correct params to diagram service."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_diagram_service.generate_diagram.return_value = {"diagram_code": ""}
            mock_get_diagram.return_value = mock_diagram_service

            message = "Generate flowchart"

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": message,
                    "include_diagram": True,
                },
            )

            # Assert
            assert response.status_code == 200
            mock_diagram_service.generate_diagram.assert_called_once_with(
                prompt=message,
                session_id=sample_session_id,
            )


class TestChatEndpointErrorHandling:
    """Test suite for error handling in chat endpoint."""

    def test_chat_should_return_404_when_session_not_found(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test chat endpoint returns 404 when session doesn't exist."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ):
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.side_effect = ValueError(
                f"Session {sample_session_id} does not exist"
            )
            mock_get_service.return_value = mock_chat_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={"message": "Test", "include_diagram": False},
            )

            # Assert
            assert response.status_code == 404
            assert "does not exist" in response.json()["detail"]

    def test_chat_should_return_500_on_processing_error(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test chat endpoint returns 500 on processing error."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ):
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.side_effect = RuntimeError(
                "Processing failed"
            )
            mock_get_service.return_value = mock_chat_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={"message": "Test", "include_diagram": False},
            )

            # Assert
            assert response.status_code == 500
            assert "Chat processing failed" in response.json()["detail"]

    def test_chat_should_call_chat_service_with_correct_params(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint calls chat_service.process_chat with correct params."""
        # Arrange
        message = "What is Python?"

        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ):
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={"message": message, "include_diagram": False},
            )

            # Assert
            assert response.status_code == 200
            mock_chat_service.process_chat.assert_called_once_with(
                session_id=sample_session_id,
                message=message,
                context_window_size=10,
            )


class TestChatEndpointRequestValidation:
    """Test suite for request validation in chat endpoint."""

    def test_chat_should_accept_include_diagram_parameter(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint accepts include_diagram parameter."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ) as mock_get_diagram:
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            mock_diagram_service = MagicMock()
            mock_diagram_service.generate_diagram.return_value = {"diagram_code": None}
            mock_get_diagram.return_value = mock_diagram_service

            # Act - with explicit include_diagram
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={
                    "message": "Test",
                    "include_diagram": True,
                },
            )

            # Assert
            assert response.status_code == 200

    def test_chat_should_require_message_field(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
    ) -> None:
        """Test chat endpoint requires message field."""
        # Act - missing message
        response = client.post(
            f"/sessions/{sample_session_id}/chat",
            json={"include_diagram": False},
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestChatEndpointResponseFormat:
    """Test suite for response format of chat endpoint."""

    def test_chat_should_return_chatresponse_model(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat endpoint returns ChatResponse model."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ):
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={"message": "Test", "include_diagram": False},
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "citations" in data
            assert "mermaid_diagram" in data
            assert isinstance(data["answer"], str)
            assert isinstance(data["citations"], list)

    def test_chat_response_citations_should_have_required_fields(
        self,
        client: TestClient,
        sample_session_id: uuid.UUID,
        sample_rag_response: RAGResponse,
    ) -> None:
        """Test chat response citations have all required fields."""
        # Arrange
        with patch(
            "backend.api.routers.sessions.get_chat_service"
        ) as mock_get_service, patch(
            "backend.api.routers.sessions.get_diagram_service"
        ):
            mock_chat_service = AsyncMock()
            mock_chat_service.process_chat.return_value = sample_rag_response
            mock_get_service.return_value = mock_chat_service

            # Act
            response = client.post(
                f"/sessions/{sample_session_id}/chat",
                json={"message": "Test", "include_diagram": False},
            )

            # Assert
            data = response.json()
            for citation in data["citations"]:
                assert "doc_name" in citation
                assert "page" in citation
                assert "section" in citation
                assert "chunk_id" in citation
                assert "source_uri" in citation
