"""
Exception hierarchy for Legal Search application.

Provides layered exception structure for domain-specific errors.
All exceptions include context for observability and debugging.

Dependencies: None (pure domain layer)
System role: Centralized exception handling across the application
"""

from typing import Any


class LegalSearchException(Exception):
    """Base exception for all Legal Search application errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize base exception with message and optional context.

        Args:
            message: Human-readable error message
            details: Optional dictionary of additional context for debugging

        """
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation including details."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ValidationError(LegalSearchException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field name that failed validation
            details: Additional context
        """
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, details)


class SessionNotFoundError(LegalSearchException):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize session not found error.

        Args:
            session_id: ID of the missing session
            details: Additional context
        """
        details = details or {}
        details["session_id"] = session_id
        super().__init__(f"Session not found: {session_id}", details)


class DocumentProcessingError(LegalSearchException):
    """Base exception for document processing errors."""

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize document processing error.

        Args:
            message: Error message
            document_id: ID of the document that failed
            details: Additional context
        """
        details = details or {}
        if document_id:
            details["document_id"] = document_id
        super().__init__(message, details)


class ParsingError(DocumentProcessingError):
    """Raised when document parsing fails."""

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        file_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize parsing error.

        Args:
            message: Error message
            document_id: ID of the document
            file_type: Type of file that failed parsing
            details: Additional context
        """
        details = details or {}
        if file_type:
            details["file_type"] = file_type
        super().__init__(message, document_id, details)


class EmbeddingError(DocumentProcessingError):
    """Raised when embedding generation fails."""

    pass


class VectorStoreError(LegalSearchException):
    """Raised when vector store operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize vector store error.

        Args:
            message: Error message
            operation: Operation that failed (upsert, query, delete)
            details: Additional context
        """
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, details)


class RetrievalError(LegalSearchException):
    """Raised when retrieval operations fail."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize retrieval error.

        Args:
            message: Error message
            session_id: Session ID for the failed retrieval
            details: Additional context
        """
        details = details or {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, details)


class ObservabilityError(LegalSearchException):
    """Raised when observability operations fail (non-critical)."""

    pass
