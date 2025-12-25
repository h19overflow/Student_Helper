"""
Exceptions for Lambda document processing.
"""

class MessageParseError(Exception):
    """Raised when SQS message cannot be parsed."""


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""
