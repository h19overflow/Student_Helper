"""
Langfuse prompt registry for versioned prompt management.

Singleton registry that automates prompt creation/versioning in Langfuse
from LangChain templates with model configuration tracking.

Dependencies: langfuse, backend.configs, backend.observability.prompt_registry
System role: Prompt version control and retrieval
"""

from typing import TYPE_CHECKING

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langfuse import Langfuse

import logging

from backend.configs import get_settings
from backend.observability.prompt_registry.converter import (
    convert_chat_template,
    convert_text_template,
)
from backend.observability.prompt_registry.models import ModelConfig

if TYPE_CHECKING:
    from langfuse.api.resources.prompts.types import Prompt

logger = logging.getLogger(__name__)


class PromptRegistry:
    """
    Singleton registry for Langfuse prompt management.

    Automates prompt versioning from LangChain templates with model
    configuration tracking. Creates new versions when prompts change.

    Attributes:
        _instance: Singleton instance
        _client: Langfuse client
        _enabled: Whether Langfuse integration is enabled

    Example:
        >>> registry = PromptRegistry()
        >>> template = ChatPromptTemplate.from_messages([
        ...     ("system", "You are a {role}"),
        ...     ("human", "{question}")
        ... ])
        >>> registry.register_prompt(
        ...     name="qa-assistant",
        ...     template=template,
        ...     config=ModelConfig(model="claude-3-sonnet", temperature=0.7),
        ...     labels=["production"]
        ... )
    """

    _instance: "PromptRegistry | None" = None
    _client: Langfuse | None = None
    _enabled: bool = False

    def __new__(cls) -> "PromptRegistry":
        """Singleton pattern for registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize Langfuse client with configuration."""
        settings = get_settings()
        obs_settings = settings.observability

        if not obs_settings.enable_tracing:
            logger.info("Langfuse tracing disabled, prompt registry inactive")
            self._enabled = False
            return

        if not obs_settings.langfuse_public_key or not obs_settings.langfuse_secret_key:
            logger.warning("Langfuse keys not configured, prompt registry inactive")
            self._enabled = False
            return

        self._client = Langfuse(
            public_key=obs_settings.langfuse_public_key,
            secret_key=obs_settings.langfuse_secret_key,
            host=obs_settings.langfuse_host,
        )
        self._enabled = True
        logger.info("Prompt registry initialized: host=%s", obs_settings.langfuse_host)

    @property
    def is_enabled(self) -> bool:
        """Check if registry is active."""
        return self._enabled

    def register_prompt(
        self,
        name: str,
        template: ChatPromptTemplate | PromptTemplate,
        config: ModelConfig,
        labels: list[str] | None = None,
    ) -> "Prompt | None":
        """
        Register or version a prompt in Langfuse.

        Creates a new prompt or adds a version if name exists. Converts
        LangChain template to Langfuse format and stores with model config.

        Args:
            name: Unique prompt identifier
            template: LangChain ChatPromptTemplate or PromptTemplate
            config: Model configuration to store with prompt
            labels: Optional labels (e.g., ["production", "staging"])

        Returns:
            Prompt: Created Langfuse prompt, or None if disabled

        Raises:
            ValueError: If template type is unsupported
        """
        if not self._enabled or self._client is None:
            logger.debug("Prompt registry disabled, skipping registration: name=%s", name)
            return None

        labels = labels or []
        langfuse_config = config.to_langfuse_config()

        if isinstance(template, ChatPromptTemplate):
            messages = convert_chat_template(template)
            prompt = self._client.create_prompt(
                name=name,
                type="chat",
                prompt=messages,
                config=langfuse_config,
                labels=labels,
            )
            logger.info(
                "Registered chat prompt: name=%s version=%s labels=%s",
                name, prompt.version, labels,
            )
            return prompt

        if isinstance(template, PromptTemplate):
            text = convert_text_template(template)
            prompt = self._client.create_prompt(
                name=name,
                type="text",
                prompt=text,
                config=langfuse_config,
                labels=labels,
            )
            logger.info(
                "Registered text prompt: name=%s version=%s labels=%s",
                name, prompt.version, labels,
            )
            return prompt

        raise ValueError(f"Unsupported template type: {type(template)}")

    def get_prompt(
        self,
        name: str,
        label: str | None = None,
        version: int | None = None,
    ) -> "Prompt | None":
        """
        Fetch prompt from Langfuse.

        Args:
            name: Prompt identifier
            label: Optional label filter (e.g., "production")
            version: Optional specific version number

        Returns:
            Prompt: Langfuse prompt object, or None if disabled/not found
        """
        if not self._enabled or self._client is None:
            logger.debug("Prompt registry disabled, cannot fetch: name=%s", name)
            return None

        kwargs: dict = {"name": name}
        if label:
            kwargs["label"] = label
        if version is not None:
            kwargs["version"] = version

        prompt = self._client.get_prompt(**kwargs)
        logger.debug(
            "Fetched prompt: name=%s version=%s",
            name, prompt.version if prompt else None,
        )
        return prompt

    def get_langchain_prompt(
        self,
        name: str,
        label: str | None = None,
        version: int | None = None,
    ) -> ChatPromptTemplate | None:
        """
        Fetch prompt from Langfuse and convert to LangChain format.

        Retrieves prompt from Langfuse and returns as ChatPromptTemplate
        with metadata attached for tracing.

        Args:
            name: Prompt identifier
            label: Optional label filter
            version: Optional specific version number

        Returns:
            ChatPromptTemplate: LangChain template, or None if disabled/not found
        """
        prompt = self.get_prompt(name, label=label, version=version)
        if prompt is None:
            return None

        # Use Langfuse's built-in LangChain conversion
        langchain_messages = prompt.get_langchain_prompt()
        template = ChatPromptTemplate.from_messages(langchain_messages)

        # Attach prompt metadata for tracing integration
        template.metadata = {"langfuse_prompt": prompt}

        return template

    def get_config(self, name: str, label: str | None = None) -> dict | None:
        """
        Get model configuration stored with prompt.

        Args:
            name: Prompt identifier
            label: Optional label filter

        Returns:
            dict: Model configuration, or None if disabled/not found
        """
        prompt = self.get_prompt(name, label=label)
        if prompt is None:
            return None
        return prompt.config
