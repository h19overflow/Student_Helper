"""
Observability module.

Provides structured logging, correlation ID tracking, Langfuse tracing,
and prompt version management.
"""

from backend.observability.prompt_registry import ModelConfig, PromptRegistry

__all__ = ["PromptRegistry", "ModelConfig"]
