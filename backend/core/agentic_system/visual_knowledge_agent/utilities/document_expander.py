"""Document expansion via recursive RAG queries.

Expands a single AI answer into ~25 related documents through parallel vector
store queries. Non-agentic approach (retrieval only, no LLM reasoning).

Dependencies: asyncio, fastapi.concurrency, vector_store, logging
System role: Document retrieval and expansion for visual knowledge pipeline
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi.concurrency import run_in_threadpool

if TYPE_CHECKING:
    from backend.boundary.vdb.base_vectors_store import BaseVectorsStore
    from backend.boundary.vdb.vector_schemas import VectorSearchResult

logger = logging.getLogger(__name__)


async def expand_documents(
    vector_store: "BaseVectorsStore",
    ai_answer: str,
    session_id: str | None = None,
) -> list["VectorSearchResult"]:
    """Expand documents from AI answer through recursive RAG queries.

    Process:
    1. Retrieve 5 relevant documents from original ai_answer
    2. For each doc, run RAG query with first 200 chars → 5 more docs
    3. Flatten all docs, deduplicate by source_uri, cap at 25

    Args:
        vector_store: Vector store instance for similarity search
        ai_answer: The AI response to expand from
        session_id: Optional session ID for multi-tenant filtering

    Returns:
        list[VectorSearchResult]: ~25 unique expanded documents

    Raises:
        Exception: If vector store queries fail
    """
    try:
        logger.info(
            f"{__name__}:expand_documents - START "
            f"answer_len={len(ai_answer)}, session_id={session_id}"
        )

        # Step 1: Initial retrieval (5 docs from ai_answer)
        logger.debug(f"{__name__}:expand_documents - Querying with ai_answer")
        initial_docs = await run_in_threadpool(
            vector_store.similarity_search,
            query=ai_answer,
            k=5,
            session_id=session_id,
        )
        logger.debug(f"{__name__}:expand_documents - Got {len(initial_docs)} initial docs")

        # Step 2: Parallel expansion (query each doc's content)
        logger.debug(f"{__name__}:expand_documents - Expanding {len(initial_docs)} docs in parallel")
        expansion_tasks = [
            run_in_threadpool(
                vector_store.similarity_search,
                query=doc.content[:200],  # Use first 200 chars as query
                k=5,
                session_id=session_id,
            )
            for doc in initial_docs
        ]

        expanded_docs_sets = await asyncio.gather(*expansion_tasks)
        logger.debug(
            f"{__name__}:expand_documents - Parallel expansion complete: "
            f"{sum(len(docs) for docs in expanded_docs_sets)} docs retrieved"
        )

        # Step 3: Flatten + deduplicate by source_uri
        all_docs = initial_docs + [d for docs in expanded_docs_sets for d in docs]
        logger.debug(f"{__name__}:expand_documents - Flattened to {len(all_docs)} total docs")

        seen_uris = set()
        unique_docs = []
        for doc in all_docs:
            uri = doc.metadata.source_uri
            if uri not in seen_uris:
                seen_uris.add(uri)
                unique_docs.append(doc)

        # Cap at 25 docs
        unique_docs = unique_docs[:25]
        logger.info(
            f"{__name__}:expand_documents - END "
            f"unique_docs={len(unique_docs)}, unique_uris={len(seen_uris)}"
        )

        return unique_docs

    except Exception as e:
        logger.error(
            f"{__name__}:expand_documents - {type(e).__name__}: {e}"
        )
        raise
