"""S3 upload node for visual knowledge pipeline.

Uploads generated image to S3 bucket and persists image metadata to database.
Final stage of LangGraph pipeline: stores S3 key instead of base64.

Dependencies: logging, asyncio, boto3, s3_uploader, image_crud, schema
System role: Fourth stage of LangGraph pipeline - persistence layer
"""

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    VisualKnowledgeState,
)
from backend.core.agentic_system.visual_knowledge_agent.utilities.s3_uploader import (
    S3ImageUploader,
)
from backend.boundary.db.CRUD.image_crud import image_crud

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)


async def s3_upload_node(
    state: VisualKnowledgeState,
    s3_uploader: S3ImageUploader,
    db_session: AsyncSession,
) -> dict:
    """
    Upload image to S3 and persist metadata to database.

    Replaces image_base64 with s3_key for efficient storage and retrieval.
    Stores all curation metadata for future reference and filtering.

    Args:
        state: Current LangGraph state with image_base64 and curation data
        s3_uploader: S3ImageUploader service for image persistence
        db_session: AsyncSession for database operations

    Returns:
        Updated state with s3_key, mime_type, and removed image_base64

    Raises:
        ValueError: If required state fields missing or image upload fails
        RuntimeError: If database persistence fails
    """
    try:
        logger.info(
            f"{__name__}:s3_upload_node - START session_id={state.get('session_id')}"
        )

        # Validate required state
        required_keys = [
            "ai_answer",
            "session_id",
            "image_base64",
            "mime_type",
            "main_concepts",
            "branches",
            "image_generation_prompt",
        ]
        for key in required_keys:
            if key not in state or not state[key]:
                raise ValueError(f"Missing required state field: {key}")

        session_id = state["session_id"]
        image_base64 = state["image_base64"]

        # Step 1: Upload image to S3
        try:
            logger.debug(
                f"{__name__}:s3_upload_node - Uploading image to S3 "
                f"size={len(image_base64)} bytes"
            )
            s3_key, detected_mime_type = await s3_uploader.upload_image(
                image_base64, session_id
            )
            logger.info(
                f"{__name__}:s3_upload_node - Image uploaded to S3 "
                f"s3_key={s3_key}"
            )
        except Exception as e:
            logger.error(
                f"{__name__}:s3_upload_node - FAILED at S3 upload - "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            raise RuntimeError(f"S3 upload failed: {e}")

        # Step 2: Persist image metadata to database
        try:
            logger.debug(
                f"{__name__}:s3_upload_node - Persisting image metadata "
                f"to database"
            )
            image_record = await image_crud.create_from_generation(
                db_session,
                session_id=session_id,
                s3_key=s3_key,
                mime_type=detected_mime_type,
                main_concepts=state["main_concepts"],
                branches=state["branches"],
                image_generation_prompt=state["image_generation_prompt"],
                message_index=state.get("message_index"),
            )
            await db_session.commit()
            logger.info(
                f"{__name__}:s3_upload_node - Image metadata persisted "
                f"image_id={image_record.id}"
            )
        except Exception as e:
            await db_session.rollback()
            logger.error(
                f"{__name__}:s3_upload_node - FAILED at database persist - "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            raise RuntimeError(f"Database persistence failed: {e}")

        # Step 3: Return updated state (remove base64, add s3_key)
        logger.info(
            f"{__name__}:s3_upload_node - END "
            f"s3_key={s3_key}, mime_type={detected_mime_type}"
        )

        return {
            "s3_key": s3_key,
            "mime_type": detected_mime_type,
            "image_base64": None,  # Clear base64 from state
            "image_id": str(image_record.id),
        }

    except ValueError as e:
        logger.error(f"{__name__}:s3_upload_node - ValueError: {e}")
        return {"error": str(e)}
    except RuntimeError as e:
        logger.error(f"{__name__}:s3_upload_node - RuntimeError: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(
            f"{__name__}:s3_upload_node - {type(e).__name__}: {e}",
            exc_info=True,
        )
        return {"error": f"Unexpected error: {e}"}
