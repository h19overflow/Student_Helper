"""Tests for PromptRegistry."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from backend.observability.prompt_registry.models import ModelConfig
from backend.observability.prompt_registry.registry import PromptRegistry


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock settings with Langfuse enabled."""
    settings = MagicMock()
    settings.observability.enable_tracing = True
    settings.observability.langfuse_public_key = "pk-test"
    settings.observability.langfuse_secret_key = "sk-test"
    settings.observability.langfuse_host = "http://localhost:3000"
    return settings


@pytest.fixture
def mock_langfuse() -> MagicMock:
    """Mock Langfuse client."""
    return MagicMock()


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset singleton before each test."""
    PromptRegistry._instance = None
    PromptRegistry._client = None
    PromptRegistry._enabled = False


class TestPromptRegistrySingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self, mock_settings: MagicMock) -> None:
        """Multiple instantiations return same instance."""
        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse"):
                registry1 = PromptRegistry()
                registry2 = PromptRegistry()
                assert registry1 is registry2

    def test_disabled_when_tracing_off(self, mock_settings: MagicMock) -> None:
        """Registry disabled when tracing disabled."""
        mock_settings.observability.enable_tracing = False
        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            registry = PromptRegistry()
            assert not registry.is_enabled

    def test_disabled_when_keys_missing(self, mock_settings: MagicMock) -> None:
        """Registry disabled when Langfuse keys missing."""
        mock_settings.observability.langfuse_public_key = None
        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            registry = PromptRegistry()
            assert not registry.is_enabled


class TestRegisterPrompt:
    """Tests for register_prompt method."""

    def test_register_chat_prompt(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Register ChatPromptTemplate creates chat type prompt."""
        mock_prompt = MagicMock()
        mock_prompt.version = 1
        mock_langfuse.create_prompt.return_value = mock_prompt

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()

                template = ChatPromptTemplate.from_messages([
                    ("system", "You are a {role}"),
                    ("human", "{question}"),
                ])
                config = ModelConfig(model="claude-3-sonnet", temperature=0.7)

                result = registry.register_prompt(
                    name="test-prompt",
                    template=template,
                    config=config,
                    labels=["production"],
                )

                assert result == mock_prompt
                mock_langfuse.create_prompt.assert_called_once()
                call_kwargs = mock_langfuse.create_prompt.call_args[1]
                assert call_kwargs["name"] == "test-prompt"
                assert call_kwargs["type"] == "chat"
                assert call_kwargs["labels"] == ["production"]
                assert call_kwargs["config"]["model"] == "claude-3-sonnet"

    def test_register_text_prompt(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Register PromptTemplate creates text type prompt."""
        mock_prompt = MagicMock()
        mock_prompt.version = 1
        mock_langfuse.create_prompt.return_value = mock_prompt

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()

                template = PromptTemplate.from_template("Hello {name}!")
                config = ModelConfig(model="gpt-4o")

                result = registry.register_prompt(
                    name="greeting",
                    template=template,
                    config=config,
                )

                assert result == mock_prompt
                call_kwargs = mock_langfuse.create_prompt.call_args[1]
                assert call_kwargs["type"] == "text"
                assert call_kwargs["prompt"] == "Hello {{name}}!"

    def test_register_when_disabled(self, mock_settings: MagicMock) -> None:
        """Register returns None when disabled."""
        mock_settings.observability.enable_tracing = False
        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            registry = PromptRegistry()

            template = ChatPromptTemplate.from_messages([("system", "test")])
            config = ModelConfig(model="test")

            result = registry.register_prompt("test", template, config)
            assert result is None


class TestGetPrompt:
    """Tests for get_prompt method."""

    def test_get_prompt_by_name(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Fetch prompt by name only."""
        mock_prompt = MagicMock()
        mock_prompt.version = 2
        mock_langfuse.get_prompt.return_value = mock_prompt

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()
                result = registry.get_prompt("my-prompt")

                assert result == mock_prompt
                mock_langfuse.get_prompt.assert_called_once_with(name="my-prompt")

    def test_get_prompt_by_label(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Fetch prompt by name and label."""
        mock_langfuse.get_prompt.return_value = MagicMock()

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()
                registry.get_prompt("my-prompt", label="production")

                mock_langfuse.get_prompt.assert_called_once_with(
                    name="my-prompt", label="production"
                )

    def test_get_prompt_by_version(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Fetch specific prompt version."""
        mock_langfuse.get_prompt.return_value = MagicMock()

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()
                registry.get_prompt("my-prompt", version=3)

                mock_langfuse.get_prompt.assert_called_once_with(
                    name="my-prompt", version=3
                )

    def test_get_prompt_when_disabled(self, mock_settings: MagicMock) -> None:
        """Get returns None when disabled."""
        mock_settings.observability.enable_tracing = False
        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            registry = PromptRegistry()
            result = registry.get_prompt("test")
            assert result is None


class TestGetLangchainPrompt:
    """Tests for get_langchain_prompt method."""

    def test_get_langchain_prompt(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Fetch and convert to LangChain format."""
        mock_prompt = MagicMock()
        mock_prompt.get_langchain_prompt.return_value = [
            ("system", "You are helpful"),
            ("human", "{question}"),
        ]
        mock_langfuse.get_prompt.return_value = mock_prompt

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()
                result = registry.get_langchain_prompt("my-prompt")

                assert isinstance(result, ChatPromptTemplate)
                assert result.metadata["langfuse_prompt"] == mock_prompt

    def test_get_langchain_prompt_when_disabled(
        self, mock_settings: MagicMock
    ) -> None:
        """Returns None when disabled."""
        mock_settings.observability.enable_tracing = False
        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            registry = PromptRegistry()
            result = registry.get_langchain_prompt("test")
            assert result is None


class TestGetConfig:
    """Tests for get_config method."""

    def test_get_config(
        self, mock_settings: MagicMock, mock_langfuse: MagicMock
    ) -> None:
        """Fetch model config from prompt."""
        mock_prompt = MagicMock()
        mock_prompt.config = {"model": "claude-3-sonnet", "temperature": 0.7}
        mock_langfuse.get_prompt.return_value = mock_prompt

        with patch("backend.observability.prompt_registry.registry.get_settings", return_value=mock_settings):
            with patch("backend.observability.prompt_registry.registry.Langfuse", return_value=mock_langfuse):
                registry = PromptRegistry()
                result = registry.get_config("my-prompt")

                assert result == {"model": "claude-3-sonnet", "temperature": 0.7}
