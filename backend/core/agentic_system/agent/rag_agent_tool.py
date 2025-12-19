"""
RAG agent search tool.

Defines the similarity search tool for retrieving relevant context.
Wraps S3VectorsStore for agent tool calling.

Dependencies: langchain.tools, backend.boundary.vdb
System role: Search tool for RAG agent context retrieval
"""

import logging
from typing import TYPE_CHECKING

from fastapi.concurrency import run_in_threadpool
from langchain_core.tools import tool

if TYPE_CHECKING:
    from backend.boundary.vdb.s3_vectors_store import S3VectorsStore

logger = logging.getLogger(__name__)


def create_search_tool(vector_store: "S3VectorsStore"):
    """
    Create a search tool bound to a S3VectorsStore instance.

    Args:
        vector_store: S3VectorsStore instance for similarity search

    Returns:
        Callable: Async tool function for similarity search
    """

    @tool
    async def search_documents(query: str, k: int = 5) -> str:
        """Search for relevant document chunks.

        Use this tool to find relevant context for answering questions.
        Returns document chunks with metadata for citation.

        Args:
            query: Search query to find relevant documents
            k: Number of results to return (default: 5)

        Returns:
            str: Formatted context with chunk metadata
        """
        logger.info(f"{__name__}:search_documents - START query_len={len(query)}, k={k}")

        try:
            logger.info(f"{__name__}:search_documents - Calling vector_store.similarity_search")
            results = await run_in_threadpool(
                vector_store.similarity_search,
                query=query,
                k=k,
            )
            logger.info(f"{__name__}:search_documents - Got {len(results)} results")
        except Exception as e:
            logger.error(f"{__name__}:search_documents - similarity_search FAILED: {type(e).__name__}: {e}")
            raise

        if not results:
            logger.warning(f"{__name__}:search_documents - No results found")
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

        output = "\n".join(formatted_chunks)
        logger.info(f"{__name__}:search_documents - END output_len={len(output)}")
        return output

    return search_documents
