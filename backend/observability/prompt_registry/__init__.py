"""
Langfuse prompt registry module.

Automates prompt versioning from LangChain ChatPromptTemplate with model
configuration tracking.

Dependencies: langfuse, langchain_core, pydantic
System role: Prompt version management and LangChain integration
"""

from backend.observability.prompt_registry.models import ModelConfig
from backend.observability.prompt_registry.registry import PromptRegistry

__all__ = ["PromptRegistry", "ModelConfig"]
