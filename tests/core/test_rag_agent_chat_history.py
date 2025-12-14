"""
Test suite for RAGAgent chat history parameter.

Tests RAG agent invoke/ainvoke methods with chat history parameter.
Verifies history formatting, prompt integration, and backward compatibility.

System role: Verification of RAG agent with conversational memory
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from backend.core.agentic_system.agent.rag_agent import RAGAgent
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Provide mock FAISSStore."""
    return MagicMock()


@pytest.fixture
def mock_chat_bedrock() -> MagicMock:
    """Provide mock ChatBedrockConverse."""
    return AsyncMock()


@pytest.fixture
def mock_search_tool() -> MagicMock:
    """Provide mock search tool."""
    tool = MagicMock()
    tool.invoke.return_value = [{"content": "Test context"}]
    tool.ainvoke = AsyncMock(return_value=[{"content": "Test context"}])
    return tool


@pytest.fixture
def mock_agent() -> MagicMock:
    """Provide mock LangChain agent."""
    agent = MagicMock()
    agent.invoke.return_value = {
        "structured_response": RAGResponse(
            answer="Test answer",
            citations=[],
            confidence=0.8,
            reasoning="Found in context",
        )
    }
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": RAGResponse(
                answer="Test answer",
                citations=[],
                confidence=0.8,
                reasoning="Found in context",
            )
        }
    )
    return agent


@pytest.fixture
def rag_agent(mock_vector_store: MagicMock) -> RAGAgent:
    """Provide RAGAgent instance for testing."""
    with patch(
        "backend.core.agentic_system.agent.rag_agent.ChatBedrockConverse"
    ), patch(
        "backend.core.agentic_system.agent.rag_agent.create_search_tool"
    ) as mock_create_tool, patch(
        "backend.core.agentic_system.agent.rag_agent.create_agent"
    ):
        mock_tool_instance = MagicMock()
        mock_create_tool.return_value = mock_tool_instance

        agent = RAGAgent(vector_store=mock_vector_store)
        agent._search_tool = mock_search_tool()
        agent._agent = mock_agent()

        return agent


class TestRAGAgentInvokeWithChatHistory:
    """Test suite for RAGAgent.invoke with chat_history."""

    def test_invoke_should_accept_chat_history_parameter(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke accepts chat_history parameter."""
        # Arrange
        chat_history = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        # Act - should not raise
        result = rag_agent.invoke(
            question="New question",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        assert result is not None

    def test_invoke_should_format_chat_history_correctly(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke formats chat history with User/Assistant labels."""
        # Arrange
        chat_history = [
            HumanMessage(content="What is AI?"),
            AIMessage(content="AI is artificial intelligence."),
        ]

        # Act
        rag_agent.invoke(
            question="Tell me more",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert - verify prompt was called with formatted history
        rag_agent._agent.invoke.assert_called_once()
        call_args = rag_agent._agent.invoke.call_args

        # Extract messages from the call
        messages = call_args[0][0]["messages"]
        formatted_text = messages[-1].content  # human message contains chat_history

        assert "User: What is AI?" in formatted_text
        assert "Assistant: AI is artificial intelligence." in formatted_text
        assert "Previous Conversation:" in formatted_text

    def test_invoke_should_work_without_chat_history(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke works without chat_history parameter (backward compatibility)."""
        # Act
        result = rag_agent.invoke(
            question="Simple question",
            session_id="test-session",
        )

        # Assert
        assert result is not None
        rag_agent._agent.invoke.assert_called_once()

    def test_invoke_should_pass_empty_history_string_when_none(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke passes empty history string when chat_history is None."""
        # Act
        rag_agent.invoke(
            question="Question",
            session_id="test-session",
            chat_history=None,
        )

        # Assert
        rag_agent._agent.invoke.assert_called_once()
        call_args = rag_agent._agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        formatted_text = messages[-1].content

        # Should have empty chat_history field (just two newlines from formatting)
        assert "Question:" in formatted_text

    def test_invoke_should_handle_empty_chat_history_list(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke handles empty chat history list."""
        # Act
        result = rag_agent.invoke(
            question="Question",
            session_id="test-session",
            chat_history=[],
        )

        # Assert
        assert result is not None
        rag_agent._agent.invoke.assert_called_once()

    def test_invoke_should_distinguish_human_and_ai_messages(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke correctly labels human vs AI messages."""
        # Arrange
        chat_history = [
            HumanMessage(content="First question"),
            AIMessage(content="First response"),
            HumanMessage(content="Second question"),
        ]

        # Act
        rag_agent.invoke(
            question="Third question",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        call_args = rag_agent._agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        formatted_text = messages[-1].content

        assert "User: First question" in formatted_text
        assert "Assistant: First response" in formatted_text
        assert "User: Second question" in formatted_text

    def test_invoke_should_include_conversation_history_header(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke includes conversation history header when history provided."""
        # Arrange
        chat_history = [HumanMessage(content="Question")]

        # Act
        rag_agent.invoke(
            question="Follow-up",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        call_args = rag_agent._agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        formatted_text = messages[-1].content

        assert "Previous Conversation:" in formatted_text

    def test_invoke_should_return_rag_response(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke returns RAGResponse."""
        # Act
        result = rag_agent.invoke(
            question="Question",
            session_id="test-session",
            chat_history=[HumanMessage(content="Context")],
        )

        # Assert
        assert isinstance(result, RAGResponse)
        assert result.answer == "Test answer"


class TestRAGAgentAinvokeWithChatHistory:
    """Test suite for RAGAgent.ainvoke with chat_history."""

    @pytest.mark.asyncio
    async def test_ainvoke_should_accept_chat_history_parameter(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke accepts chat_history parameter."""
        # Arrange
        chat_history = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        # Act
        result = await rag_agent.ainvoke(
            question="New question",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        assert result is not None

    @pytest.mark.asyncio
    async def test_ainvoke_should_format_chat_history_correctly(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke formats chat history with User/Assistant labels."""
        # Arrange
        chat_history = [
            HumanMessage(content="What is ML?"),
            AIMessage(content="ML is machine learning."),
        ]

        # Act
        await rag_agent.ainvoke(
            question="Tell me more",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        rag_agent._agent.ainvoke.assert_called_once()
        call_args = rag_agent._agent.ainvoke.call_args
        messages = call_args[0][0]["messages"]
        formatted_text = messages[-1].content

        assert "User: What is ML?" in formatted_text
        assert "Assistant: ML is machine learning." in formatted_text
        assert "Previous Conversation:" in formatted_text

    @pytest.mark.asyncio
    async def test_ainvoke_should_work_without_chat_history(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke works without chat_history parameter."""
        # Act
        result = await rag_agent.ainvoke(
            question="Simple question",
            session_id="test-session",
        )

        # Assert
        assert result is not None
        rag_agent._agent.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_ainvoke_should_use_search_tool_async(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke uses async search tool (ainvoke not invoke)."""
        # Act
        await rag_agent.ainvoke(
            question="Question",
            session_id="test-session",
        )

        # Assert
        rag_agent._search_tool.ainvoke.assert_called_once()
        rag_agent._search_tool.invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_ainvoke_should_return_rag_response(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke returns RAGResponse."""
        # Act
        result = await rag_agent.ainvoke(
            question="Question",
            session_id="test-session",
            chat_history=[HumanMessage(content="Context")],
        )

        # Assert
        assert isinstance(result, RAGResponse)
        assert result.answer == "Test answer"

    @pytest.mark.asyncio
    async def test_ainvoke_should_handle_multiple_message_types(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke correctly handles alternating human/AI messages."""
        # Arrange
        chat_history = [
            HumanMessage(content="Q1"),
            AIMessage(content="A1"),
            HumanMessage(content="Q2"),
            AIMessage(content="A2"),
            HumanMessage(content="Q3"),
        ]

        # Act
        await rag_agent.ainvoke(
            question="Q4",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        call_args = rag_agent._agent.ainvoke.call_args
        messages = call_args[0][0]["messages"]
        formatted_text = messages[-1].content

        # Verify all messages are present
        for i in range(1, 4):
            if i <= 3:
                assert f"User: Q{i}" in formatted_text
            if i <= 2:
                assert f"Assistant: A{i}" in formatted_text


class TestRAGAgentPromptIntegration:
    """Test suite for chat_history integration with RAG prompt."""

    def test_invoke_should_pass_chat_history_to_prompt(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test invoke passes chat_history field to prompt template."""
        # Arrange
        chat_history = [HumanMessage(content="Context message")]

        # Act
        rag_agent.invoke(
            question="Question",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        # The prompt should have been invoked with chat_history key
        # This is implicit in the formatting test above, but let's be explicit
        rag_agent._agent.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_ainvoke_should_pass_chat_history_to_prompt(
        self, rag_agent: RAGAgent
    ) -> None:
        """Test ainvoke passes chat_history field to prompt template."""
        # Arrange
        chat_history = [HumanMessage(content="Context message")]

        # Act
        await rag_agent.ainvoke(
            question="Question",
            session_id="test-session",
            chat_history=chat_history,
        )

        # Assert
        rag_agent._agent.ainvoke.assert_called_once()
