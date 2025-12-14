"""Comprehensive tests for RAG Q&A agent implementation.

Tests all components:
- rag_agent_schema.py: RAGCitation and RAGResponse Pydantic schemas
- rag_agent_prompt.py: System prompt and Langfuse registry integration
- rag_agent_tool.py: search_documents tool factory
- rag_agent.py: RAGAgent class orchestration

Dependencies: pytest, unittest.mock, pydantic, langchain_core
System role: Agent response schema validation, prompt templates, tool output formatting
"""

from typing import Any
from unittest.mock import MagicMock, Mock, patch, AsyncMock
import pytest
from pydantic import ValidationError
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from backend.core.agentic_system.agent.rag_agent_schema import RAGCitation, RAGResponse
from backend.core.agentic_system.agent.rag_agent_prompt import (
    RAG_AGENT_PROMPT,
    RAG_PROMPT_NAME,
    SYSTEM_PROMPT,
    get_rag_prompt,
    register_rag_prompt,
)
from backend.core.agentic_system.agent.rag_agent_tool import create_search_tool
from backend.core.agentic_system.agent.rag_agent import RAGAgent
from backend.boundary.vdb.vector_schemas import VectorMetadata, VectorSearchResult


# ============================================================================
# RAGCitation Schema Tests
# ============================================================================


class TestRAGCitationSchema:
    """Test RAGCitation Pydantic model validation."""

    def test_citation_creation_with_all_fields(self) -> None:
        """Should create citation with all fields provided."""
        citation = RAGCitation(
            chunk_id="chunk-123",
            content_snippet="The capital of France is Paris",
            page=5,
            section="Geography",
            source_uri="documents/france.pdf",
            relevance_score=0.95,
        )

        assert citation.chunk_id == "chunk-123"
        assert citation.content_snippet == "The capital of France is Paris"
        assert citation.page == 5
        assert citation.section == "Geography"
        assert citation.source_uri == "documents/france.pdf"
        assert citation.relevance_score == 0.95

    def test_citation_creation_with_defaults(self) -> None:
        """Should create citation with optional fields defaulting to None."""
        citation = RAGCitation(
            chunk_id="chunk-456",
            content_snippet="Some content",
            source_uri="documents/test.pdf",
            relevance_score=0.75,
        )

        assert citation.chunk_id == "chunk-456"
        assert citation.page is None
        assert citation.section is None

    def test_citation_validation_missing_chunk_id(self) -> None:
        """Should raise validation error when chunk_id missing."""
        with pytest.raises(ValidationError):
            RAGCitation(  # type: ignore[call-arg]
                content_snippet="test",
                source_uri="test.pdf",
                relevance_score=0.5,
            )

    def test_citation_validation_missing_source_uri(self) -> None:
        """Should raise validation error when source_uri missing."""
        with pytest.raises(ValidationError):
            RAGCitation(  # type: ignore[call-arg]
                chunk_id="chunk-123",
                content_snippet="test",
                relevance_score=0.5,
            )

    def test_citation_validation_invalid_relevance_score(self) -> None:
        """Should validate relevance_score is float."""
        with pytest.raises(ValidationError):
            RAGCitation(  # type: ignore[call-arg]
                chunk_id="chunk-123",
                content_snippet="test",
                source_uri="test.pdf",
                relevance_score="high",
            )

    def test_citation_relevance_score_bounds(self) -> None:
        """Relevance score should accept values between 0.0 and 1.0."""
        # Valid boundaries
        RAGCitation(
            chunk_id="test",
            content_snippet="test",
            source_uri="test.pdf",
            relevance_score=0.0,
        )
        RAGCitation(
            chunk_id="test",
            content_snippet="test",
            source_uri="test.pdf",
            relevance_score=1.0,
        )
        RAGCitation(
            chunk_id="test",
            content_snippet="test",
            source_uri="test.pdf",
            relevance_score=0.5,
        )

    def test_citation_serialization(self) -> None:
        """Should serialize to JSON dict."""
        citation = RAGCitation(
            chunk_id="chunk-789",
            content_snippet="Test snippet",
            page=10,
            section="Introduction",
            source_uri="documents/intro.pdf",
            relevance_score=0.88,
        )

        data = citation.model_dump()

        assert data["chunk_id"] == "chunk-789"
        assert data["page"] == 10
        assert data["relevance_score"] == 0.88


# ============================================================================
# RAGResponse Schema Tests
# ============================================================================


class TestRAGResponseSchema:
    """Test RAGResponse Pydantic model validation."""

    def test_response_creation_with_all_fields(self) -> None:
        """Should create response with all fields populated."""
        citations = [
            RAGCitation(
                chunk_id="chunk-1",
                content_snippet="Paris is the capital",
                source_uri="wiki.pdf",
                relevance_score=0.95,
            ),
        ]

        response = RAGResponse(
            answer="The capital of France is Paris",
            citations=citations,
            confidence=0.98,
            reasoning="Found in context chunk-1 which directly states this fact",
        )

        assert response.answer == "The capital of France is Paris"
        assert len(response.citations) == 1
        assert response.confidence == 0.98
        assert response.reasoning == "Found in context chunk-1 which directly states this fact"

    def test_response_creation_with_defaults(self) -> None:
        """Should create response with default values."""
        response = RAGResponse(answer="Test answer")

        assert response.answer == "Test answer"
        assert response.citations == []
        assert response.confidence == 0.0
        assert response.reasoning == ""

    def test_response_validation_missing_answer(self) -> None:
        """Should raise validation error when answer missing."""
        with pytest.raises(ValidationError):
            RAGResponse()  # type: ignore[call-arg]

    def test_response_citations_list_type(self) -> None:
        """Citations must be a list of RAGCitation objects."""
        with pytest.raises(ValidationError):
            RAGResponse(
                answer="test",
                citations="not a list",  # type: ignore[assignment]
            )

    def test_response_confidence_bounds(self) -> None:
        """Confidence must be between 0.0 and 1.0."""
        # Valid values
        RAGResponse(answer="test", confidence=0.0)
        RAGResponse(answer="test", confidence=1.0)
        RAGResponse(answer="test", confidence=0.5)

        # Invalid: below 0.0
        with pytest.raises(ValidationError):
            RAGResponse(answer="test", confidence=-0.1)

        # Invalid: above 1.0
        with pytest.raises(ValidationError):
            RAGResponse(answer="test", confidence=1.1)

    def test_response_with_multiple_citations(self) -> None:
        """Should handle multiple citations."""
        citations = [
            RAGCitation(
                chunk_id="chunk-1",
                content_snippet="Paris is capital",
                source_uri="wiki.pdf",
                relevance_score=0.95,
            ),
            RAGCitation(
                chunk_id="chunk-2",
                content_snippet="France is in Europe",
                source_uri="geography.pdf",
                relevance_score=0.87,
            ),
        ]

        response = RAGResponse(answer="test answer", citations=citations, confidence=0.9)

        assert len(response.citations) == 2
        assert response.citations[0].chunk_id == "chunk-1"
        assert response.citations[1].chunk_id == "chunk-2"

    def test_response_serialization(self) -> None:
        """Should serialize to JSON dict."""
        citations = [
            RAGCitation(
                chunk_id="chunk-1",
                content_snippet="snippet",
                source_uri="test.pdf",
                relevance_score=0.92,
            ),
        ]

        response = RAGResponse(
            answer="The answer is 42",
            citations=citations,
            confidence=0.85,
            reasoning="Based on context",
        )

        data = response.model_dump()

        assert data["answer"] == "The answer is 42"
        assert len(data["citations"]) == 1
        assert data["confidence"] == 0.85
        assert data["reasoning"] == "Based on context"

    def test_response_deserialization(self) -> None:
        """Should deserialize from JSON dict."""
        data = {
            "answer": "Test answer",
            "citations": [
                {
                    "chunk_id": "chunk-1",
                    "content_snippet": "test snippet",
                    "page": 5,
                    "section": "Test Section",
                    "source_uri": "test.pdf",
                    "relevance_score": 0.88,
                }
            ],
            "confidence": 0.9,
            "reasoning": "Test reasoning",
        }

        response = RAGResponse(**data)

        assert response.answer == "Test answer"
        assert len(response.citations) == 1
        assert response.citations[0].chunk_id == "chunk-1"


# ============================================================================
# RAG Prompt Template Tests
# ============================================================================


class TestRAGPromptTemplate:
    """Test RAG prompt template structure and variables."""

    def test_prompt_is_chat_template(self) -> None:
        """RAG_AGENT_PROMPT should be a ChatPromptTemplate."""
        assert isinstance(RAG_AGENT_PROMPT, ChatPromptTemplate)

    def test_prompt_has_required_variables(self) -> None:
        """Prompt should have context and question variables."""
        variables = RAG_AGENT_PROMPT.input_variables
        assert "context" in variables
        assert "question" in variables

    def test_system_prompt_content(self) -> None:
        """System prompt should provide RAG instructions."""
        assert "helpful study assistant" in SYSTEM_PROMPT.lower()
        assert "citation" in SYSTEM_PROMPT.lower() or "cite" in SYSTEM_PROMPT.lower()

    def test_prompt_template_rendering(self) -> None:
        """Should render prompt with context and question."""
        rendered = RAG_AGENT_PROMPT.invoke({
            "context": "Paris is the capital of France.",
            "question": "What is the capital of France?",
        })

        messages = rendered.to_messages()
        assert len(messages) >= 2  # At least system and human messages

    def test_rag_prompt_name_constant(self) -> None:
        """RAG_PROMPT_NAME should be set."""
        assert RAG_PROMPT_NAME == "rag-qa-agent"


# ============================================================================
# Prompt Registry Tests
# ============================================================================


class TestPromptRegistry:
    """Test prompt registry integration."""

    @patch("backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry")
    def test_register_rag_prompt_when_enabled(self, mock_registry_class: Mock) -> None:
        """Should register prompt when registry is enabled."""
        mock_registry = MagicMock()
        mock_registry.is_enabled = True
        mock_registry_class.return_value = mock_registry

        register_rag_prompt(
            model_id="test-model",
            temperature=0.5,
            labels=["test"],
        )

        mock_registry.register_prompt.assert_called_once()
        call_kwargs = mock_registry.register_prompt.call_args[1]
        assert call_kwargs["name"] == RAG_PROMPT_NAME
        assert call_kwargs["labels"] == ["test"]

    @patch("backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry")
    def test_register_rag_prompt_when_disabled(self, mock_registry_class: Mock) -> None:
        """Should skip registration when registry is disabled."""
        mock_registry = MagicMock()
        mock_registry.is_enabled = False
        mock_registry_class.return_value = mock_registry

        register_rag_prompt()

        mock_registry.register_prompt.assert_not_called()

    @patch("backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry")
    def test_register_rag_prompt_default_label(self, mock_registry_class: Mock) -> None:
        """Should use default label when not provided."""
        mock_registry = MagicMock()
        mock_registry.is_enabled = True
        mock_registry_class.return_value = mock_registry

        register_rag_prompt()

        call_kwargs = mock_registry.register_prompt.call_args[1]
        assert call_kwargs["labels"] == ["development"]

    @patch("backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry")
    def test_get_rag_prompt_from_registry(self, mock_registry_class: Mock) -> None:
        """Should fetch prompt from registry when enabled."""
        mock_registry = MagicMock()
        mock_registry.is_enabled = True
        mock_template = MagicMock(spec=ChatPromptTemplate)
        mock_registry.get_langchain_prompt.return_value = mock_template
        mock_registry_class.return_value = mock_registry

        result = get_rag_prompt(use_registry=True)

        mock_registry.get_langchain_prompt.assert_called_once_with(
            RAG_PROMPT_NAME,
            label=None,
        )
        assert result == mock_template

    @patch("backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry")
    def test_get_rag_prompt_from_registry_with_label(self, mock_registry_class: Mock) -> None:
        """Should pass label when fetching from registry."""
        mock_registry = MagicMock()
        mock_registry.is_enabled = True
        mock_template = MagicMock(spec=ChatPromptTemplate)
        mock_registry.get_langchain_prompt.return_value = mock_template
        mock_registry_class.return_value = mock_registry

        result = get_rag_prompt(use_registry=True, label="production")

        mock_registry.get_langchain_prompt.assert_called_once_with(
            RAG_PROMPT_NAME,
            label="production",
        )

    @patch("backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry")
    def test_get_rag_prompt_fallback_to_local(self, mock_registry_class: Mock) -> None:
        """Should fallback to local template when registry returns None."""
        mock_registry = MagicMock()
        mock_registry.is_enabled = True
        mock_registry.get_langchain_prompt.return_value = None
        mock_registry_class.return_value = mock_registry

        result = get_rag_prompt(use_registry=True)

        assert result == RAG_AGENT_PROMPT

    def test_get_rag_prompt_local_when_not_using_registry(self) -> None:
        """Should return local prompt when use_registry is False."""
        result = get_rag_prompt(use_registry=False)

        assert result == RAG_AGENT_PROMPT


# ============================================================================
# Search Tool Tests
# ============================================================================


class TestSearchTool:
    """Test search_documents tool factory and output."""

    def test_create_search_tool_returns_callable(self) -> None:
        """create_search_tool should return a tool object with invoke method."""
        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = []

        tool = create_search_tool(mock_vector_store)

        # StructuredTool has invoke method, not directly callable
        assert hasattr(tool, "invoke")
        assert tool.name == "search_documents"

    def test_search_tool_with_no_results(self) -> None:
        """Should return message when no results found."""
        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = []

        tool = create_search_tool(mock_vector_store)
        result = tool.invoke({"query": "test query", "k": 5})

        assert result == "No relevant documents found."

    def test_search_tool_formats_single_result(self) -> None:
        """Should format single search result correctly."""
        mock_metadata = MagicMock()
        mock_metadata.page = 5
        mock_metadata.section = "Introduction"
        mock_metadata.source_uri = "documents/test.pdf"

        mock_result = MagicMock()
        mock_result.chunk_id = "chunk-123"
        mock_result.content = "Test content here"
        mock_result.metadata = mock_metadata
        mock_result.similarity_score = 0.95

        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = [mock_result]

        tool = create_search_tool(mock_vector_store)
        result = tool.invoke({"query": "test query", "k": 5})

        assert "chunk-123" in result
        assert "Test content here" in result
        assert "0.950" in result
        assert "documents/test.pdf" in result

    def test_search_tool_formats_multiple_results(self) -> None:
        """Should format multiple results with separator."""
        mock_results = []
        for i in range(3):
            mock_metadata = MagicMock()
            mock_metadata.page = i + 1
            mock_metadata.section = f"Section {i}"
            mock_metadata.source_uri = f"doc_{i}.pdf"

            mock_result = MagicMock()
            mock_result.chunk_id = f"chunk-{i}"
            mock_result.content = f"Content {i}"
            mock_result.metadata = mock_metadata
            mock_result.similarity_score = 0.9 - (i * 0.05)

            mock_results.append(mock_result)

        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = mock_results

        tool = create_search_tool(mock_vector_store)
        result = tool.invoke({"query": "test query", "k": 5})

        # Should contain all chunks
        assert "chunk-0" in result
        assert "chunk-1" in result
        assert "chunk-2" in result

        # Should have separators
        assert result.count("---") >= 6  # At least 3 results with opening and closing

    def test_search_tool_calls_vector_store(self) -> None:
        """Should call vector_store.similarity_search with correct params."""
        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = []

        tool = create_search_tool(mock_vector_store)
        tool.invoke({"query": "test query", "k": 10})

        mock_vector_store.similarity_search.assert_called_once()
        call_kwargs = mock_vector_store.similarity_search.call_args[1]
        assert call_kwargs["query"] == "test query"
        assert call_kwargs["k"] == 10

    def test_search_tool_default_k_value(self) -> None:
        """Should use default k=5 when not specified."""
        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = []

        tool = create_search_tool(mock_vector_store)
        tool.invoke({"query": "test query"})

        call_kwargs = mock_vector_store.similarity_search.call_args[1]
        assert call_kwargs["k"] == 5


# ============================================================================
# RAGAgent Class Tests
# ============================================================================


class TestRAGAgentInitialization:
    """Test RAGAgent initialization and configuration."""

    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_agent_initialization(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
    ) -> None:
        """Should initialize agent with vector store and model."""
        mock_vector_store = MagicMock()
        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        agent = RAGAgent(vector_store=mock_vector_store)

        assert agent._vector_store == mock_vector_store
        assert agent._model == mock_model
        assert agent._use_prompt_registry is False

    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_agent_initialization_with_custom_params(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
    ) -> None:
        """Should use custom model_id, region, and temperature."""
        mock_vector_store = MagicMock()
        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        agent = RAGAgent(
            vector_store=mock_vector_store,
            model_id="custom-model-id",
            region="us-west-2",
            temperature=0.7,
        )

        mock_bedrock.assert_called_once()
        call_kwargs = mock_bedrock.call_args[1]
        assert call_kwargs["model"] == "custom-model-id"
        assert call_kwargs["region_name"] == "us-west-2"
        assert call_kwargs["temperature"] == 0.7

    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_agent_creates_search_tool(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
    ) -> None:
        """Should create search tool from vector store."""
        mock_vector_store = MagicMock()
        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        agent = RAGAgent(vector_store=mock_vector_store)

        # search_tool should be created
        assert agent._search_tool is not None

    @patch("backend.core.agentic_system.agent.rag_agent.register_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_agent_registers_prompt_when_enabled(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_register_prompt: Mock,
    ) -> None:
        """Should register prompt when use_prompt_registry is True."""
        mock_vector_store = MagicMock()
        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        agent = RAGAgent(
            vector_store=mock_vector_store,
            use_prompt_registry=True,
            prompt_label="production",
        )

        mock_register_prompt.assert_called_once()
        call_kwargs = mock_register_prompt.call_args[1]
        assert call_kwargs["labels"] == ["production"]

    @patch("backend.core.agentic_system.agent.rag_agent.register_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_agent_skips_prompt_registration_when_disabled(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_register_prompt: Mock,
    ) -> None:
        """Should not register prompt when use_prompt_registry is False."""
        mock_vector_store = MagicMock()
        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        agent = RAGAgent(vector_store=mock_vector_store, use_prompt_registry=False)

        mock_register_prompt.assert_not_called()


class TestRAGAgentInvoke:
    """Test RAGAgent invoke method."""

    @patch("backend.core.agentic_system.agent.rag_agent.get_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_invoke_calls_agent(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_get_prompt: Mock,
    ) -> None:
        """Should call agent with formatted prompt and context."""
        mock_vector_store = MagicMock()
        mock_search_tool = MagicMock()
        mock_search_tool.invoke.return_value = "Found content"

        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        mock_agent = MagicMock()
        mock_response = RAGResponse(answer="Test answer")
        mock_agent.invoke.return_value = {"structured_response": mock_response}
        mock_create_agent.return_value = mock_agent

        mock_template = MagicMock()
        mock_template.invoke.return_value.to_messages.return_value = []
        mock_get_prompt.return_value = mock_template

        agent = RAGAgent(vector_store=mock_vector_store)
        agent._search_tool = mock_search_tool

        result = agent.invoke("What is the answer?")

        assert isinstance(result, RAGResponse)
        assert result.answer == "Test answer"
        mock_agent.invoke.assert_called_once()

    @patch("backend.core.agentic_system.agent.rag_agent.get_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_invoke_uses_registry_when_enabled(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_get_prompt: Mock,
    ) -> None:
        """Should use registry when use_prompt_registry is True."""
        mock_vector_store = MagicMock()
        mock_search_tool = MagicMock()
        mock_search_tool.invoke.return_value = "Found content"

        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        mock_agent = MagicMock()
        mock_response = RAGResponse(answer="Test answer")
        mock_agent.invoke.return_value = {"structured_response": mock_response}
        mock_create_agent.return_value = mock_agent

        mock_template = MagicMock()
        mock_template.invoke.return_value.to_messages.return_value = []
        mock_get_prompt.return_value = mock_template

        agent = RAGAgent(
            vector_store=mock_vector_store,
            use_prompt_registry=True,
            prompt_label="prod",
        )
        agent._search_tool = mock_search_tool

        with patch("backend.core.agentic_system.agent.rag_agent.register_rag_prompt"):
            result = agent.invoke("What is the answer?")

        mock_get_prompt.assert_called_once()
        call_kwargs = mock_get_prompt.call_args[1]
        assert call_kwargs["use_registry"] is True
        assert call_kwargs["label"] == "prod"

    @patch("backend.core.agentic_system.agent.rag_agent.get_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_invoke_returns_rag_response(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_get_prompt: Mock,
    ) -> None:
        """Should return RAGResponse with answer and citations."""
        mock_vector_store = MagicMock()
        mock_search_tool = MagicMock()
        mock_search_tool.invoke.return_value = "context"

        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        citation = RAGCitation(
            chunk_id="chunk-1",
            content_snippet="test",
            source_uri="test.pdf",
            relevance_score=0.9,
        )
        mock_response = RAGResponse(
            answer="The answer",
            citations=[citation],
            confidence=0.95,
        )
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"structured_response": mock_response}
        mock_create_agent.return_value = mock_agent

        mock_template = MagicMock()
        mock_template.invoke.return_value.to_messages.return_value = []
        mock_get_prompt.return_value = mock_template

        agent = RAGAgent(vector_store=mock_vector_store)
        agent._search_tool = mock_search_tool

        result = agent.invoke("question")

        assert result.answer == "The answer"
        assert len(result.citations) == 1
        assert result.citations[0].chunk_id == "chunk-1"
        assert result.confidence == 0.95


class TestRAGAgentAinvoke:
    """Test RAGAgent async invoke method."""

    @pytest.mark.asyncio
    @patch("backend.core.agentic_system.agent.rag_agent.get_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    async def test_ainvoke_async_execution(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_get_prompt: Mock,
    ) -> None:
        """Should execute async invoke."""
        mock_vector_store = MagicMock()

        mock_search_tool = AsyncMock()
        mock_search_tool.ainvoke.return_value = "async context"

        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        mock_response = RAGResponse(answer="Async answer")
        mock_agent = MagicMock()
        mock_agent_ainvoke = AsyncMock()
        mock_agent_ainvoke.return_value = {"structured_response": mock_response}
        mock_agent.ainvoke = mock_agent_ainvoke
        mock_create_agent.return_value = mock_agent

        mock_template = MagicMock()
        mock_template.invoke.return_value.to_messages.return_value = []
        mock_get_prompt.return_value = mock_template

        agent = RAGAgent(vector_store=mock_vector_store)
        agent._search_tool = mock_search_tool

        result = await agent.ainvoke("question")

        assert isinstance(result, RAGResponse)
        assert result.answer == "Async answer"
        mock_search_tool.ainvoke.assert_called_once()
        mock_agent_ainvoke.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================


class TestRAGAgentIntegration:
    """Integration tests for complete RAG workflow."""

    @patch("backend.core.agentic_system.agent.rag_agent.get_rag_prompt")
    @patch("backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse")
    @patch("backend.core.agentic_system.agent.rag_agent.create_agent")
    def test_agent_workflow_end_to_end(
        self,
        mock_create_agent: Mock,
        mock_bedrock: Mock,
        mock_get_prompt: Mock,
    ) -> None:
        """Should complete end-to-end workflow."""
        # Setup mock vector store with realistic response
        mock_vector_store = MagicMock()
        mock_search_tool = MagicMock()

        # Simulate search results
        mock_search_tool.invoke.return_value = (
            "---\n"
            "chunk_id: chunk-1\n"
            "page: 5\n"
            "section: Geography\n"
            "source_uri: france.pdf\n"
            "relevance_score: 0.950\n"
            "\n"
            "Paris is the capital of France.\n"
            "---"
        )

        mock_model = MagicMock()
        mock_bedrock.return_value = mock_model

        mock_response = RAGResponse(
            answer="Paris is the capital of France.",
            citations=[
                RAGCitation(
                    chunk_id="chunk-1",
                    content_snippet="Paris is the capital of France.",
                    page=5,
                    section="Geography",
                    source_uri="france.pdf",
                    relevance_score=0.95,
                )
            ],
            confidence=0.98,
            reasoning="Direct statement found in source material.",
        )
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"structured_response": mock_response}
        mock_create_agent.return_value = mock_agent

        mock_template = MagicMock()
        mock_template.invoke.return_value.to_messages.return_value = []
        mock_get_prompt.return_value = mock_template

        # Create and invoke agent
        agent = RAGAgent(vector_store=mock_vector_store)
        agent._search_tool = mock_search_tool

        result = agent.invoke("What is the capital of France?")

        # Verify complete response
        assert result.answer == "Paris is the capital of France."
        assert len(result.citations) == 1
        assert result.citations[0].source_uri == "france.pdf"
        assert result.confidence == 0.98


class TestRAGAgentImports:
    """Test all module imports work correctly."""

    def test_import_rag_agent_schema(self) -> None:
        """Should import RAGCitation and RAGResponse."""
        assert RAGCitation is not None
        assert RAGResponse is not None

    def test_import_rag_agent_prompt(self) -> None:
        """Should import prompt functions."""
        assert RAG_AGENT_PROMPT is not None
        assert register_rag_prompt is not None
        assert get_rag_prompt is not None

    def test_import_rag_agent_tool(self) -> None:
        """Should import tool factory."""
        assert create_search_tool is not None

    def test_import_rag_agent(self) -> None:
        """Should import RAGAgent class."""
        assert RAGAgent is not None

    def test_imports_are_correct_types(self) -> None:
        """Imported objects should have correct types."""
        assert isinstance(RAG_AGENT_PROMPT, ChatPromptTemplate)
        assert callable(register_rag_prompt)
        assert callable(get_rag_prompt)
        assert callable(create_search_tool)
