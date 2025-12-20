"""Visual knowledge service layer.

Orchestrates visual knowledge generation pipeline.
Coordinates between API layer and agent layer.

Dependencies: logging, agent, models, S3 client
System role: Service layer for visual knowledge feature
"""

import logging

from backend.boundary.aws.s3_client import S3DocumentClient
from backend.core.agentic_system.visual_knowledge_agent.visual_knowledge_agent import (
    VisualKnowledgeAgent,
)
from backend.models.visual_knowledge import VisualKnowledgeResponseModel

logger = logging.getLogger(__name__)


class VisualKnowledgeService:
    """Service for generating visual knowledge diagrams.

    Handles orchestration between API and agent layers.
    Generates presigned URLs for efficient S3 image access.
    """

    def __init__(
        self,
        visual_knowledge_agent: VisualKnowledgeAgent,
        s3_client: S3DocumentClient,
    ) -> None:
        """Initialize service with dependencies.

        Args:
            visual_knowledge_agent: VisualKnowledgeAgent instance
            s3_client: S3DocumentClient for presigned URL generation
        """
        self._agent = visual_knowledge_agent
        self._s3_client = s3_client

    async def generate(
        self,
        session_id: str,
        ai_answer: str,
        message_index: int,
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
            message_index: Index of the message in chat history for sorting

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
                message_index=message_index,
            )

            # Generate presigned URL for S3 key
            # Note: agent returns S3 key in image_base64 field for backward compatibility
            s3_key = result.image_base64
            logger.debug(f"{__name__}:generate - Generating presigned URL for s3_key={s3_key}")
            presigned_url, expires_at = self._s3_client.generate_presigned_download_url(
                s3_key=s3_key,
                expires_in=3600,
            )
            logger.debug(f"{__name__}:generate - Presigned URL: {presigned_url[:100]}...")

            logger.info(
                f"{__name__}:generate - END "
                f"concepts={len(result.main_concepts)}, "
                f"branches={len(result.branches)}, "
                f"image_key_len={len(s3_key)}"
            )

            # Convert to response model with presigned URL
            # Remove image_base64 as it's not a field in the response model
            result_dict = result.model_dump(exclude={"image_base64"})
            result_dict["s3_key"] = s3_key
            result_dict["presigned_url"] = presigned_url
            result_dict["expires_at"] = expires_at.isoformat()

            return VisualKnowledgeResponseModel(**result_dict)

        except ValueError as e:
            logger.error(f"{__name__}:generate - ValueError: {e}")
            raise
        except Exception as e:
            logger.error(f"{__name__}:generate - {type(e).__name__}: {e}")
            raise
