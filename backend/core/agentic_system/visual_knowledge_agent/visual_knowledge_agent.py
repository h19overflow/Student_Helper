"""Visual knowledge agent with LangGraph orchestration.

Main agent class that:
1. Initializes Google Gemini client, curation agent, and S3 uploader
2. Creates LangGraph for stateful pipeline with S3 persistence
3. Provides async interface to run complete visual knowledge generation

Dependencies: google.genai, langchain.agents, LangGraph, boto3, schema, graph definition
System role: Main orchestrator for visual knowledge pipeline
"""

import logging
from typing import TYPE_CHECKING

import boto3
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
from backend.core.agentic_system.visual_knowledge_agent.utilities.s3_uploader import (
    S3ImageUploader,
)
from backend.configs import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.boundary.vdb.base_vectors_store import BaseVectorsStore

logger = logging.getLogger(__name__)


class VisualKnowledgeAgent:
    """Agent for generating interactive visual knowledge diagrams.

    Orchestrates:
    1. Document expansion via RAG
    2. Concept curation via LLM
    3. Diagram generation via Gemini
    4. S3 upload and persistence
    """

    def __init__(
        self,
        google_api_key: str,
        vector_store: "BaseVectorsStore",
        db_session: "AsyncSession",
        model_id: str = "gemini-3-flash-preview",
        temperature: float = 0.0,
    ) -> None:
        """Initialize visual knowledge agent with dependencies.

        Args:
            google_api_key: Google API key for Gemini access
            vector_store: Vector store for document retrieval
            db_session: AsyncSession for database operations
            model_id: Google model ID for curation agent (default: gemini-3-flash)
            temperature: Model temperature for LLM (default: 0.0)

        Raises:
            ValueError: If google_api_key is not provided
        """
        if not google_api_key:
            raise ValueError("google_api_key is required")
        if not db_session:
            raise ValueError("db_session is required")

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

        # Initialize S3 uploader
        logger.debug(f"{__name__}:__init__ - Initializing S3 uploader")
        settings = get_settings()
        s3_client = boto3.client(
            "s3",
            region_name=settings.s3_documents.region,
        )
        self._s3_uploader = S3ImageUploader(
            s3_client=s3_client,
            bucket_name=settings.s3_documents.bucket,
        )

        # Store database session
        self._db_session = db_session

        # Create LangGraph pipeline
        logger.debug(f"{__name__}:__init__ - Creating LangGraph pipeline")
        self._graph = create_visual_knowledge_graph(
            vector_store=vector_store,
            curation_agent=self._curation_agent,
            google_client=self._google_client,
            s3_uploader=self._s3_uploader,
            db_session=self._db_session,
        )

        logger.info(f"{__name__}:__init__ - VisualKnowledgeAgent initialized successfully")

    async def ainvoke(
        self,
        ai_answer: str,
        session_id: str | None = None,
        message_index: int | None = None,
    ) -> VisualKnowledgeResponse:
        """Generate visual knowledge diagram from AI answer.

        Executes LangGraph pipeline:
        1. Document expansion (RAG)
        2. Concept curation (LLM)
        3. Image generation (Gemini)
        4. S3 upload and persistence

        Args:
            ai_answer: The assistant's response to visualize
            session_id: Optional session ID for filtering
            message_index: Index of the message in chat history for sorting

        Returns:
            VisualKnowledgeResponse: Complete diagram with S3 location and metadata

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
                "message_index": message_index,
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

            # Validate required outputs (s3_key now instead of image_base64)
            required_keys = [
                "s3_key",
                "mime_type",
                "main_concepts",
                "branches",
                "image_generation_prompt",
            ]
            for key in required_keys:
                if key not in final_state or not final_state[key]:
                    raise ValueError(f"Missing required output: {key}")

            # Build response with S3 key instead of base64
            response = VisualKnowledgeResponse(
                image_base64=final_state["s3_key"],  # S3 key stored in this field
                mime_type=final_state["mime_type"],
                main_concepts=final_state["main_concepts"],
                branches=final_state["branches"],
                image_generation_prompt=final_state["image_generation_prompt"],
            )

            logger.info(
                f"{__name__}:ainvoke - END "
                f"concepts={len(response.main_concepts)}, "
                f"branches={len(response.branches)}, "
                f"s3_key={final_state['s3_key']}"
            )

            return response

        except ValueError as e:
            logger.error(f"{__name__}:ainvoke - ValueError: {e}")
            raise
        except Exception as e:
            logger.error(f"{__name__}:ainvoke - {type(e).__name__}: {e}")
            raise
