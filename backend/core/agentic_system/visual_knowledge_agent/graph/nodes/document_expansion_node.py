"""Document expansion node for visual knowledge pipeline.

Retrieves ~25 documents through recursive RAG queries on the AI answer.

Dependencies: logging, vector_store, document_expander
System role: First stage of LangGraph pipeline
"""

import logging
from typing import TYPE_CHECKING

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    VisualKnowledgeState,
)
from backend.core.agentic_system.visual_knowledge_agent.utilities.document_expander import (
    expand_documents,
)

if TYPE_CHECKING:
    from backend.boundary.vdb.base_vectors_store import BaseVectorsStore

logger = logging.getLogger(__name__)


async def document_expansion_node(
    state: VisualKnowledgeState,
    vector_store: "BaseVectorsStore",
) -> dict:
    """Expand documents from AI answer via RAG queries.

    Retrieves ~25 documents through recursive vector store queries.
    Updates state with expanded_docs.

    Args:
        state: LangGraph state with ai_answer input
        vector_store: Vector store for similarity search

    Returns:
        dict: State update with expanded_docs or error
    """
    try:
        logger.info(
            f"{__name__}:document_expansion_node - START "
            f"answer_len={len(state['ai_answer'])}"
        )

        expanded_docs = await expand_documents(
            vector_store=vector_store,
            ai_answer=state["ai_answer"],
            session_id=state.get("session_id"),
        )

        logger.info(
            f"{__name__}:document_expansion_node - END "
            f"expanded_docs={len(expanded_docs)}"
        )

        return {"expanded_docs": expanded_docs}

    except Exception as e:
        logger.error(
            f"{__name__}:document_expansion_node - {type(e).__name__}: {e}"
        )
        return {"error": str(e)}
