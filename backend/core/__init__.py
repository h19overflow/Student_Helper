"""
Core business logic module.

Contains domain business logic, exception hierarchy, and core components.
All business rules and domain-specific logic reside here.
"""

from backend.core.exceptions import (
    LegalSearchException,
    ValidationError,
    SessionNotFoundError,
    DocumentProcessingError,
    ParsingError,
    EmbeddingError,
    VectorStoreError,
    RetrievalError,
    ObservabilityError,
)

__all__ = [
    "LegalSearchException",
    "ValidationError",
    "SessionNotFoundError",
    "DocumentProcessingError",
    "ParsingError",
    "EmbeddingError",
    "VectorStoreError",
    "RetrievalError",
    "ObservabilityError",
]
