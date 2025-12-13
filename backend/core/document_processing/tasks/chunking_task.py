"""
Text chunking task using RecursiveCharacterTextSplitter.

Splits documents into retrievable chunks while preserving context.

Dependencies: langchain_text_splitters
System role: Second stage of document ingestion pipeline
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class ChunkingTask:
    """Split documents into chunks using RecursiveCharacterTextSplitter."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        """
        Initialize chunking task with splitter configuration.

        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between consecutive chunks
        """
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
            length_function=len,
        )

    def chunk(self, documents: list[Document]) -> list[Document]:
        """
        Split documents into chunks.

        Args:
            documents: LangChain Documents to split

        Returns:
            list[Document]: Chunked documents with preserved metadata

        Raises:
            ValueError: When documents list is empty
        """
        if not documents:
            raise ValueError("No documents to chunk")

        return self._splitter.split_documents(documents)
