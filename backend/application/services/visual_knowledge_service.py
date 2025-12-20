"""Visual knowledge service layer.

Orchestrates visual knowledge generation pipeline.
Coordinates between API layer and agent layer.

Dependencies: logging, agent, models
System role: Service layer for visual knowledge feature
"""

import logging

from backend.core.agentic_system.visual_knowledge_agent.visual_knowledge_agent import (
    VisualKnowledgeAgent,
)
from backend.models.visual_knowledge import VisualKnowledgeResponseModel

logger = logging.getLogger(__name__)


class VisualKnowledgeService:
    """Service for generating visual knowledge diagrams.

    Handles orchestration between API and agent layers.
    """

    def __init__(self, visual_knowledge_agent: VisualKnowledgeAgent) -> None:
        """Initialize service with agent dependency.

        Args:
            visual_knowledge_agent: VisualKnowledgeAgent instance
        """
        self._agent = visual_knowledge_agent

    async def generate(
        self,
        session_id: str,
        ai_answer: str,
    ) -> VisualKnowledgeResponseModel:
        """Generate visual knowledge diagram from AI answer.

        Process:
        1. Expand documents from answer (RAG)
        2. Curate concepts and create image prompt
        3. Generate diagram via Gemini
        4. Return structured response

        Args:
            session_id: Session ID for context
            ai_answer: The assistant response to visualize

        Returns:
            VisualKnowledgeResponseModel: Diagram with metadata

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If generation fails
        """
        try:
            logger.info(
                f"{__name__}:generate - START "
                f"session_id={session_id}, answer_len={len(ai_answer)}"
            )

            # Call agent orchestrator
            result = await self._agent.ainvoke(
                ai_answer=ai_answer,
                session_id=session_id,
            )

            logger.info(
                f"{__name__}:generate - END "
                f"concepts={len(result.main_concepts)}, "
                f"branches={len(result.branches)}, "
                f"image_len={len(result.image_base64)}"
            )

            # Convert to response model
            return VisualKnowledgeResponseModel(**result.model_dump())

        except ValueError as e:
            logger.error(f"{__name__}:generate - ValueError: {e}")
            raise
        except Exception as e:
            logger.error(f"{__name__}:generate - {type(e).__name__}: {e}")
            raise
