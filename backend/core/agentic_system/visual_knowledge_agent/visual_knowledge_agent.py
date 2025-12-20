"""Visual knowledge agent with LangGraph orchestration.

Main agent class that:
1. Initializes Google Gemini client and curation agent
2. Creates LangGraph for stateful pipeline
3. Provides async interface to run complete visual knowledge generation

Dependencies: google.genai, langchain.agents, LangGraph, schema, graph definition
System role: Main orchestrator for visual knowledge pipeline
"""

import logging
from typing import TYPE_CHECKING

from google import genai
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    CurationResult,
    VisualKnowledgeResponse,
    VisualKnowledgeState,
)
from backend.core.agentic_system.visual_knowledge_agent.graph.visual_knowledge_graph import (
    create_visual_knowledge_graph,
)

if TYPE_CHECKING:
    from backend.boundary.vdb.base_vectors_store import BaseVectorsStore

logger = logging.getLogger(__name__)


class VisualKnowledgeAgent:
    """Agent for generating interactive visual knowledge diagrams.

    Orchestrates:
    1. Document expansion via RAG
    2. Concept curation via LLM
    3. Diagram generation via Gemini
    """

    def __init__(
        self,
        google_api_key: str,
        vector_store: "BaseVectorsStore",
        model_id: str = "gemini-3-flash-preview",
        temperature: float = 0.0,
    ) -> None:
        """Initialize visual knowledge agent with dependencies.

        Args:
            google_api_key: Google API key for Gemini access
            vector_store: Vector store for document retrieval
            model_id: Google model ID for curation agent (default: gemini-3-flash)
            temperature: Model temperature for LLM (default: 0.0)

        Raises:
            ValueError: If google_api_key is not provided
        """
        if not google_api_key:
            raise ValueError("google_api_key is required")

        logger.info(f"{__name__}:__init__ - Initializing VisualKnowledgeAgent")

        # Initialize Google Gemini client
        logger.debug(f"{__name__}:__init__ - Creating Google Gemini client")
        self._google_client = genai.Client(api_key=google_api_key)

        # Initialize curation agent with structured output
        logger.debug(
            f"{__name__}:__init__ - Creating curation agent with {model_id}"
        )
        self._curation_agent = create_agent(
            model=f"google_genai:{model_id}",
            tools=[],  # No tools needed; agent processes documents in prompt
            response_format=ToolStrategy(CurationResult),
        )

        # Create LangGraph pipeline
        logger.debug(f"{__name__}:__init__ - Creating LangGraph pipeline")
        self._graph = create_visual_knowledge_graph(
            vector_store=vector_store,
            curation_agent=self._curation_agent,
            google_client=self._google_client,
        )

        logger.info(f"{__name__}:__init__ - VisualKnowledgeAgent initialized successfully")

    async def ainvoke(
        self,
        ai_answer: str,
        session_id: str | None = None,
    ) -> VisualKnowledgeResponse:
        """Generate visual knowledge diagram from AI answer.

        Executes LangGraph pipeline:
        1. Document expansion (RAG)
        2. Concept curation (LLM)
        3. Image generation (Gemini)

        Args:
            ai_answer: The assistant's response to visualize
            session_id: Optional session ID for filtering

        Returns:
            VisualKnowledgeResponse: Complete diagram with metadata

        Raises:
            RuntimeError: If graph execution fails at any step
            ValueError: If required inputs are missing
        """
        try:
            logger.info(
                f"{__name__}:ainvoke - START "
                f"answer_len={len(ai_answer)}, session_id={session_id}"
            )

            # Validate inputs
            if not ai_answer or not ai_answer.strip():
                raise ValueError("ai_answer cannot be empty")

            # Create initial state
            initial_state: VisualKnowledgeState = {
                "ai_answer": ai_answer,
                "session_id": session_id,
            }

            # Run graph (async)
            logger.debug(f"{__name__}:ainvoke - Executing LangGraph pipeline")
            final_state = await self._graph.ainvoke(initial_state)

            # Check for errors in state
            if "error" in final_state and final_state["error"]:
                error_msg = final_state["error"]
                logger.error(
                    f"{__name__}:ainvoke - Graph execution failed: {error_msg}"
                )
                raise RuntimeError(f"Visual knowledge generation failed: {error_msg}")

            # Validate required outputs
            required_keys = [
                "image_base64",
                "mime_type",
                "main_concepts",
                "branches",
                "image_generation_prompt",
            ]
            for key in required_keys:
                if key not in final_state or not final_state[key]:
                    raise ValueError(f"Missing required output: {key}")

            # Build response
            response = VisualKnowledgeResponse(
                image_base64=final_state["image_base64"],
                mime_type=final_state["mime_type"],
                main_concepts=final_state["main_concepts"],
                branches=final_state["branches"],
                image_generation_prompt=final_state["image_generation_prompt"],
            )

            logger.info(
                f"{__name__}:ainvoke - END "
                f"concepts={len(response.main_concepts)}, "
                f"branches={len(response.branches)}, "
                f"image_len={len(response.image_base64)}"
            )

            return response

        except ValueError as e:
            logger.error(f"{__name__}:ainvoke - ValueError: {e}")
            raise
        except Exception as e:
            logger.error(f"{__name__}:ainvoke - {type(e).__name__}: {e}")
            raise
