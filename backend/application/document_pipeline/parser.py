"""
Document parser using Docling.

Parses various document formats into structured chunks.

Dependencies: docling, backend.models.chunk
System role: Document parsing adapter
"""

from backend.models.chunk import Chunk


class DocumentParser:
    """Docling document parser."""

    def __init__(self) -> None:
        """Initialize Docling parser."""
        pass

    def parse_document(self, file_path: str) -> list[Chunk]:
        """
        Parse document into chunks.

        Args:
            file_path: Path to document

        Returns:
            list[Chunk]: Parsed chunks
        """
        pass

    def extract_metadata(self, file_path: str) -> dict:
        """Extract document metadata."""
        pass
