"""
Test suite for RAG prompt template.

Tests RAG agent system prompt rendering with and without chat history.
Verifies prompt template structure and variable substitution.

System role: Verification of RAG prompt template
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.core.agentic_system.agent.rag_agent_prompt import (
    get_rag_prompt,
    RAG_AGENT_PROMPT,
    register_rag_prompt,
)


class TestRAGPromptTemplate:
    """Test suite for RAG agent prompt template."""

    def test_prompt_should_have_system_and_human_messages(self) -> None:
        """Test RAG_AGENT_PROMPT has system and human message templates."""
        # Act
        messages = RAG_AGENT_PROMPT.messages

        # Assert
        assert len(messages) >= 2
        assert messages[0][0] == "system"
        assert messages[1][0] == "human"

    def test_prompt_should_include_conversation_history_in_system(self) -> None:
        """Test system prompt includes conversation history section."""
        # Act
        system_content = RAG_AGENT_PROMPT.messages[0][1]

        # Assert
        assert "Conversation History" in system_content
        assert "follow-up questions" in system_content

    def test_prompt_should_have_chat_history_variable(self) -> None:
        """Test human message template includes {chat_history} variable."""
        # Act
        human_template = RAG_AGENT_PROMPT.messages[1][1]

        # Assert
        assert "{chat_history}" in human_template

    def test_prompt_should_have_context_variable(self) -> None:
        """Test human message template includes {context} variable."""
        # Act
        human_template = RAG_AGENT_PROMPT.messages[1][1]

        # Assert
        assert "{context}" in human_template

    def test_prompt_should_have_question_variable(self) -> None:
        """Test human message template includes {question} variable."""
        # Act
        human_template = RAG_AGENT_PROMPT.messages[1][1]

        # Assert
        assert "{question}" in human_template

    def test_prompt_should_render_with_context_and_question(self) -> None:
        """Test prompt can be rendered with context and question."""
        # Arrange
        test_context = "Test context data"
        test_question = "What is the answer?"

        # Act
        rendered = RAG_AGENT_PROMPT.invoke({
            "context": test_context,
            "question": test_question,
            "chat_history": "",
        })

        # Assert
        rendered_str = str(rendered)
        assert test_question in rendered_str
        assert test_context in rendered_str

    def test_prompt_should_render_with_chat_history(self) -> None:
        """Test prompt renders correctly when chat_history is provided."""
        # Arrange
        history = "Previous Conversation:\nUser: Hello\nAssistant: Hi there"

        # Act
        rendered = RAG_AGENT_PROMPT.invoke({
            "context": "Test",
            "question": "Question?",
            "chat_history": history,
        })

        # Assert
        rendered_str = str(rendered)
        assert history in rendered_str

    def test_prompt_should_render_with_empty_chat_history(self) -> None:
        """Test prompt renders correctly when chat_history is empty."""
        # Act
        rendered = RAG_AGENT_PROMPT.invoke({
            "context": "Test context",
            "question": "Test question",
            "chat_history": "",
        })

        # Assert
        rendered_str = str(rendered)
        assert "Test context" in rendered_str
        assert "Test question" in rendered_str

    def test_prompt_should_include_citation_instructions(self) -> None:
        """Test system prompt includes citation instructions."""
        # Act
        system_content = RAG_AGENT_PROMPT.messages[0][1]

        # Assert
        assert "cite" in system_content.lower()
        assert "citation" in system_content.lower()
        assert "chunk_id" in system_content

    def test_prompt_should_include_context_format_description(self) -> None:
        """Test system prompt describes context format."""
        # Act
        system_content = RAG_AGENT_PROMPT.messages[0][1]

        # Assert
        assert "Context Format" in system_content
        assert "chunk_id" in system_content
        assert "content" in system_content
        assert "source_uri" in system_content

    def test_prompt_should_include_response_guidelines(self) -> None:
        """Test system prompt includes response guidelines."""
        # Act
        system_content = RAG_AGENT_PROMPT.messages[0][1]

        # Assert
        assert "Response Guidelines" in system_content
        assert "concise" in system_content.lower()
        assert "accurate" in system_content.lower()

    def test_prompt_should_instruct_to_use_only_provided_context(self) -> None:
        """Test system prompt instructs to use only provided context."""
        # Act
        system_content = RAG_AGENT_PROMPT.messages[0][1]

        # Assert
        assert "ONLY" in system_content or "only" in system_content
        assert "context" in system_content.lower()


class TestGetRagPrompt:
    """Test suite for get_rag_prompt factory function."""

    def test_get_rag_prompt_should_return_prompt_template(self) -> None:
        """Test get_rag_prompt returns ChatPromptTemplate."""
        # Act
        prompt = get_rag_prompt(use_registry=False)

        # Assert
        assert prompt is not None
        assert hasattr(prompt, "invoke")

    def test_get_rag_prompt_should_return_default_prompt_when_registry_disabled(
        self,
    ) -> None:
        """Test get_rag_prompt returns local template when registry disabled."""
        # Act
        prompt = get_rag_prompt(use_registry=False)

        # Assert
        assert prompt == RAG_AGENT_PROMPT

    def test_get_rag_prompt_should_use_registry_when_enabled(self) -> None:
        """Test get_rag_prompt attempts registry when use_registry=True."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry.get_langchain_prompt.return_value = RAG_AGENT_PROMPT
            mock_registry_class.return_value = mock_registry

            # Act
            prompt = get_rag_prompt(use_registry=True)

            # Assert
            mock_registry.get_langchain_prompt.assert_called_once()
            assert prompt is not None

    def test_get_rag_prompt_should_pass_label_to_registry(self) -> None:
        """Test get_rag_prompt passes label to registry."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry.get_langchain_prompt.return_value = RAG_AGENT_PROMPT
            mock_registry_class.return_value = mock_registry

            # Act
            get_rag_prompt(use_registry=True, label="production")

            # Assert
            mock_registry.get_langchain_prompt.assert_called_once_with(
                "rag-qa-agent", label="production"
            )

    def test_get_rag_prompt_should_return_default_when_registry_not_found(
        self,
    ) -> None:
        """Test get_rag_prompt returns default when prompt not in registry."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry.get_langchain_prompt.return_value = None
            mock_registry_class.return_value = mock_registry

            # Act
            prompt = get_rag_prompt(use_registry=True)

            # Assert
            assert prompt == RAG_AGENT_PROMPT

    def test_get_rag_prompt_should_return_default_when_registry_disabled(
        self,
    ) -> None:
        """Test get_rag_prompt returns default when registry is disabled."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = False
            mock_registry_class.return_value = mock_registry

            # Act
            prompt = get_rag_prompt(use_registry=True)

            # Assert
            assert prompt == RAG_AGENT_PROMPT


class TestRegisterRagPrompt:
    """Test suite for register_rag_prompt function."""

    def test_register_rag_prompt_should_not_fail_when_registry_disabled(
        self,
    ) -> None:
        """Test register_rag_prompt gracefully handles disabled registry."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = False
            mock_registry_class.return_value = mock_registry

            # Act - should not raise
            register_rag_prompt()

            # Assert
            mock_registry.register_prompt.assert_not_called()

    def test_register_rag_prompt_should_register_when_enabled(self) -> None:
        """Test register_rag_prompt registers prompt when registry enabled."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class, patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.ModelConfig"
        ) as mock_config_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry_class.return_value = mock_registry

            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            # Act
            register_rag_prompt()

            # Assert
            mock_registry.register_prompt.assert_called_once()

    def test_register_rag_prompt_should_accept_model_id(self) -> None:
        """Test register_rag_prompt accepts custom model_id."""
        # Arrange
        custom_model_id = "custom.model.id"
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class, patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.ModelConfig"
        ) as mock_config_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry_class.return_value = mock_registry

            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            # Act
            register_rag_prompt(model_id=custom_model_id)

            # Assert
            mock_config_class.assert_called_once()
            call_kwargs = mock_config_class.call_args.kwargs
            assert call_kwargs["model"] == custom_model_id

    def test_register_rag_prompt_should_accept_temperature(self) -> None:
        """Test register_rag_prompt accepts custom temperature."""
        # Arrange
        custom_temp = 0.5
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class, patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.ModelConfig"
        ) as mock_config_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry_class.return_value = mock_registry

            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            # Act
            register_rag_prompt(temperature=custom_temp)

            # Assert
            mock_config_class.assert_called_once()
            call_kwargs = mock_config_class.call_args.kwargs
            assert call_kwargs["temperature"] == custom_temp

    def test_register_rag_prompt_should_accept_labels(self) -> None:
        """Test register_rag_prompt accepts custom labels."""
        # Arrange
        custom_labels = ["production", "v2"]
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class, patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.ModelConfig"
        ) as mock_config_class:
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry_class.return_value = mock_registry

            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            # Act
            register_rag_prompt(labels=custom_labels)

            # Assert
            mock_registry.register_prompt.assert_called_once()
            call_kwargs = mock_registry.register_prompt.call_args.kwargs
            assert call_kwargs["labels"] == custom_labels

    def test_register_rag_prompt_should_use_development_label_by_default(
        self,
    ) -> None:
        """Test register_rag_prompt uses development label when none provided."""
        # Arrange
        with patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.PromptRegistry"
        ) as mock_registry_class, patch(
            "backend.core.agentic_system.agent.rag_agent_prompt.ModelConfig"
        ):
            mock_registry = MagicMock()
            mock_registry.is_enabled = True
            mock_registry_class.return_value = mock_registry

            # Act
            register_rag_prompt(labels=None)

            # Assert
            call_kwargs = mock_registry.register_prompt.call_args.kwargs
            assert call_kwargs["labels"] == ["development"]
