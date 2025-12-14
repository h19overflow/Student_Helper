"""
RAG agent search tool.

Defines the similarity search tool for retrieving relevant context.
Wraps FAISSStore for agent tool calling.

Dependencies: langchain.tools, backend.boundary.vdb
System role: Search tool for RAG agent context retrieval
"""

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from backend.boundary.vdb.faiss_store import FAISSStore


def create_search_tool(vector_store: "FAISSStore"):
    """
    Create a search tool bound to a FAISSStore instance.

    Args:
        vector_store: FAISSStore instance for similarity search

    Returns:
        Callable: Tool function for similarity search
    """

    @tool
    def search_documents(query: str, k: int = 5) -> str:
        """Search for relevant document chunks.

        Use this tool to find relevant context for answering questions.
        Returns document chunks with metadata for citation.

        Args:
            query: Search query to find relevant documents
            k: Number of results to return (default: 5)

        Returns:
            str: Formatted context with chunk metadata
        """
        results = vector_store.similarity_search(query=query, k=k)

        if not results:
            return "No relevant documents found."

        formatted_chunks = []
        for result in results:
            chunk_text = f"""---
chunk_id: {result.chunk_id}
page: {result.metadata.page}
section: {result.metadata.section}
source_uri: {result.metadata.source_uri}
relevance_score: {result.similarity_score:.3f}

{result.content}
---"""
            formatted_chunks.append(chunk_text)

        return "\n".join(formatted_chunks)

    return search_documents
