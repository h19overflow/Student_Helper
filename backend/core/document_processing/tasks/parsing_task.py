"""
Document parsing task using Docling.

Converts PDF, DOCX, and other document formats into LangChain Documents.

Dependencies: langchain_docling
System role: First stage of document ingestion pipeline
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_docling import DoclingLoader


class ParsingError(Exception):
    """Raised when document parsing fails."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        self.file_path = file_path
        super().__init__(message)


class ParsingTask:
    """Parse documents into LangChain Documents using Docling."""

    def __init__(self, export_type: str = "markdown") -> None:
        """
        Initialize parsing task.

        Args:
            export_type: Export format - "markdown" or "doc_chunks"
        """
        self._export_type = export_type

    def parse(self, file_path: str) -> list[Document]:
        """
        Parse document file into LangChain Documents.

        Args:
            file_path: Path to document (local path or URL)

        Returns:
            list[Document]: Parsed documents with content and metadata

        Raises:
            ParsingError: When document parsing fails
        """
        path = Path(file_path)
        if not path.exists():
            raise ParsingError(f"File not found: {file_path}", file_path)

        try:
            loader = DoclingLoader(
                file_path=file_path,
                export_type=self._export_type,
            )
            documents = loader.load()
            return documents
        except Exception as e:
            raise ParsingError(f"Failed to parse document: {e}", file_path) from e
