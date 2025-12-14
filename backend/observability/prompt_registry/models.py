"""
Pydantic models for prompt registry configuration.

Defines model configuration schema for LLM parameters tracked alongside prompts.

Dependencies: pydantic
System role: Configuration validation for prompt-model pairs
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """
    LLM model configuration tracked with prompts.

    Stores model parameters alongside prompts in Langfuse for version tracking
    and reproducibility.

    Attributes:
        model: LLM model identifier (e.g., "claude-3-sonnet", "gpt-4o")
        temperature: Sampling temperature (0.0-2.0)
        top_p: Nucleus sampling parameter
        max_tokens: Maximum tokens in response
        extra: Additional model-specific parameters
    """

    model: str = Field(description="LLM model identifier")
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens in response",
    )
    extra: dict[str, Any] | None = Field(
        default=None,
        description="Additional model-specific parameters",
    )

    def to_langfuse_config(self) -> dict[str, Any]:
        """
        Convert to Langfuse config dictionary.

        Returns:
            dict: Configuration dict for Langfuse prompt creation
        """
        config: dict[str, Any] = {"model": self.model}

        if self.temperature is not None:
            config["temperature"] = self.temperature
        if self.top_p is not None:
            config["top_p"] = self.top_p
        if self.max_tokens is not None:
            config["max_tokens"] = self.max_tokens
        if self.extra:
            config.update(self.extra)

        return config
