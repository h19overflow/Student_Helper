"""LangGraph definition for visual knowledge pipeline.

Builds and compiles a stateful graph that orchestrates:
1. Document expansion (RAG)
2. Concept curation (LLM)
3. Image generation (Gemini)
4. S3 upload and persistence

Dependencies: langgraph, node functions, schema, s3_uploader
System role: Graph orchestration for visual knowledge pipeline
"""

import logging
from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    VisualKnowledgeState,
)
from backend.core.agentic_system.visual_knowledge_agent.graph.nodes import (
    curation_node,
    document_expansion_node,
    image_generation_node,
    s3_upload_node,
)
from backend.core.agentic_system.visual_knowledge_agent.utilities.s3_uploader import (
    S3ImageUploader,
)

if TYPE_CHECKING:
    from google import genai
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.boundary.vdb.base_vectors_store import BaseVectorsStore
    from backend.core.agentic_system.agent.rag_agent import RAGAgent

logger = logging.getLogger(__name__)


def create_visual_knowledge_graph(
    vector_store: "BaseVectorsStore",
    curation_agent: "RAGAgent",
    google_client: "genai.Client",
    s3_uploader: S3ImageUploader,
    db_session: "AsyncSession",
) -> "StateGraph":
    """Create LangGraph for visual knowledge pipeline.

    Builds stateful graph with four sequential nodes:
    1. document_expansion: Expand docs via RAG
    2. curation: Extract concepts and image prompt
    3. image_generation: Generate diagram
    4. s3_upload: Persist to S3 and database

    Args:
        vector_store: Vector store for document retrieval
        curation_agent: LangChain agent for concept curation
        google_client: Google Generative AI client
        s3_uploader: S3ImageUploader service for image persistence
        db_session: AsyncSession for database operations

    Returns:
        CompiledGraph: Compiled and runnable graph

    Raises:
        Exception: If graph compilation fails
    """
    try:
        logger.info(f"{__name__}:create_visual_knowledge_graph - Building graph")

        # Create graph with state schema
        graph = StateGraph(VisualKnowledgeState)

        # Define node wrappers with dependency injection
        async def expansion_wrapper(state):
            return await document_expansion_node(state, vector_store)

        async def curation_wrapper(state):
            return await curation_node(state, curation_agent)

        async def generation_wrapper(state):
            return await image_generation_node(state, google_client)

        async def upload_wrapper(state):
            return await s3_upload_node(state, s3_uploader, db_session)

        # Add nodes
        logger.debug(
            f"{__name__}:create_visual_knowledge_graph - Adding document_expansion node"
        )
        graph.add_node("document_expansion", expansion_wrapper)

        logger.debug(
            f"{__name__}:create_visual_knowledge_graph - Adding curation node"
        )
        graph.add_node("curation", curation_wrapper)

        logger.debug(
            f"{__name__}:create_visual_knowledge_graph - Adding image_generation node"
        )
        graph.add_node("image_generation", generation_wrapper)

        logger.debug(
            f"{__name__}:create_visual_knowledge_graph - Adding s3_upload node"
        )
        graph.add_node("s3_upload", upload_wrapper)

        # Define pipeline flow (linear: expansion → curation → generation → upload)
        logger.debug(f"{__name__}:create_visual_knowledge_graph - Setting entry point")
        graph.set_entry_point("document_expansion")

        logger.debug(
            f"{__name__}:create_visual_knowledge_graph - Adding edges"
        )
        graph.add_edge("document_expansion", "curation")
        graph.add_edge("curation", "image_generation")
        graph.add_edge("image_generation", "s3_upload")
        graph.add_edge("s3_upload", END)

        # Compile graph
        logger.debug(f"{__name__}:create_visual_knowledge_graph - Compiling graph")
        compiled_graph = graph.compile()

        logger.info(f"{__name__}:create_visual_knowledge_graph - Graph created successfully")
        return compiled_graph

    except Exception as e:
        logger.error(
            f"{__name__}:create_visual_knowledge_graph - {type(e).__name__}: {e}"
        )
        raise
