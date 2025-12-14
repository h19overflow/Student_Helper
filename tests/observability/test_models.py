"""Tests for prompt registry models."""

import pytest
from pydantic import ValidationError

from backend.observability.prompt_registry.models import ModelConfig


class TestModelConfig:
    """Tests for ModelConfig Pydantic schema."""

    def test_model_required(self) -> None:
        """Model field is required."""
        with pytest.raises(ValidationError):
            ModelConfig()  # type: ignore[call-arg]

    def test_minimal_config(self) -> None:
        """Create config with only required model field."""
        config = ModelConfig(model="claude-3-sonnet")
        assert config.model == "claude-3-sonnet"
        assert config.temperature is None
        assert config.top_p is None
        assert config.max_tokens is None
        assert config.extra is None

    def test_full_config(self) -> None:
        """Create config with all fields populated."""
        config = ModelConfig(
            model="gpt-4o",
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            extra={"stop": ["\n"]},
        )
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.max_tokens == 1000
        assert config.extra == {"stop": ["\n"]}

    def test_temperature_bounds(self) -> None:
        """Temperature must be between 0.0 and 2.0."""
        # Valid bounds
        ModelConfig(model="test", temperature=0.0)
        ModelConfig(model="test", temperature=2.0)

        # Invalid: too low
        with pytest.raises(ValidationError):
            ModelConfig(model="test", temperature=-0.1)

        # Invalid: too high
        with pytest.raises(ValidationError):
            ModelConfig(model="test", temperature=2.1)

    def test_top_p_bounds(self) -> None:
        """Top_p must be between 0.0 and 1.0."""
        ModelConfig(model="test", top_p=0.0)
        ModelConfig(model="test", top_p=1.0)

        with pytest.raises(ValidationError):
            ModelConfig(model="test", top_p=-0.1)

        with pytest.raises(ValidationError):
            ModelConfig(model="test", top_p=1.1)

    def test_max_tokens_positive(self) -> None:
        """Max tokens must be positive."""
        ModelConfig(model="test", max_tokens=1)

        with pytest.raises(ValidationError):
            ModelConfig(model="test", max_tokens=0)

        with pytest.raises(ValidationError):
            ModelConfig(model="test", max_tokens=-1)

    def test_to_langfuse_config_minimal(self) -> None:
        """Convert minimal config to Langfuse format."""
        config = ModelConfig(model="claude-3-sonnet")
        result = config.to_langfuse_config()

        assert result == {"model": "claude-3-sonnet"}

    def test_to_langfuse_config_full(self) -> None:
        """Convert full config to Langfuse format."""
        config = ModelConfig(
            model="gpt-4o",
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            extra={"stop": ["\n"], "seed": 42},
        )
        result = config.to_langfuse_config()

        assert result == {
            "model": "gpt-4o",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1000,
            "stop": ["\n"],
            "seed": 42,
        }

    def test_to_langfuse_config_partial(self) -> None:
        """Convert partial config omits None values."""
        config = ModelConfig(model="test", temperature=0.5)
        result = config.to_langfuse_config()

        assert result == {"model": "test", "temperature": 0.5}
        assert "top_p" not in result
        assert "max_tokens" not in result
