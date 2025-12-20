"""LangGraph definition for visual knowledge pipeline.

Builds and compiles a stateful graph that orchestrates:
1. Document expansion (RAG)
2. Concept curation (LLM)
3. Image generation (Gemini)

Dependencies: langgraph, node functions, schema
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
)

if TYPE_CHECKING:
    from google import genai

    from backend.boundary.vdb.base_vectors_store import BaseVectorsStore
    from backend.core.agentic_system.agent.rag_agent import RAGAgent

logger = logging.getLogger(__name__)


def create_visual_knowledge_graph(
    vector_store: "BaseVectorsStore",
    curation_agent: "RAGAgent",
    google_client: "genai.Client",
) -> "StateGraph":
    """Create LangGraph for visual knowledge pipeline.

    Builds stateful graph with three sequential nodes:
    1. document_expansion: Expand docs via RAG
    2. curation: Extract concepts and image prompt
    3. image_generation: Generate diagram

    Args:
        vector_store: Vector store for document retrieval
        curation_agent: LangChain agent for concept curation
        google_client: Google Generative AI client

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

        def curation_wrapper(state):
            return curation_node(state, curation_agent)

        def generation_wrapper(state):
            return image_generation_node(state, google_client)

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

        # Define pipeline flow (linear: expansion → curation → generation)
        logger.debug(f"{__name__}:create_visual_knowledge_graph - Setting entry point")
        graph.set_entry_point("document_expansion")

        logger.debug(
            f"{__name__}:create_visual_knowledge_graph - Adding edges"
        )
        graph.add_edge("document_expansion", "curation")
        graph.add_edge("curation", "image_generation")
        graph.add_edge("image_generation", END)

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
