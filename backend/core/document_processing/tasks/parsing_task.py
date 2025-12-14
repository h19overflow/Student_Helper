"""
Document parsing task using LangChain PyPDFLoader.

Converts PDF documents into LangChain Documents.

Dependencies: langchain_community.document_loaders
System role: First stage of document ingestion pipeline
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


class ParsingError(Exception):
    """Raised when document parsing fails."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        self.file_path = file_path
        super().__init__(message)


class ParsingTask:
    """Parse PDF documents into LangChain Documents."""

    def __init__(self, export_type: str = "markdown") -> None:
        """
        Initialize parsing task.

        Args:
            export_type: Export format (deprecated, kept for compatibility)
        """
        self._export_type = export_type

    def parse(self, file_path: str) -> list[Document]:
        """
        Parse PDF document into LangChain Documents.

        Args:
            file_path: Path to PDF document

        Returns:
            list[Document]: Parsed documents with content and metadata

        Raises:
            ParsingError: When document parsing fails
        """
        path = Path(file_path)
        if not path.exists():
            raise ParsingError(f"File not found: {file_path}", file_path)

        if not path.suffix.lower() == ".pdf":
            raise ParsingError(
                f"Unsupported file format: {path.suffix}. Only PDF files are supported.",
                file_path,
            )

        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            if not documents:
                raise ParsingError("PDF document contains no extractable text", file_path)

            return documents

        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Failed to parse PDF: {e}", file_path) from e
