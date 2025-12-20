"""Visual Knowledge diagram generation endpoints.

Routes:
- POST /sessions/{session_id}/visual-knowledge - Generate visual knowledge diagram from AI response
- GET /sessions/{session_id}/images - Retrieve all images for a session (for session resuming)

Dependencies: backend.application.services.visual_knowledge_service, image_crud, S3 client
System role: Visual knowledge diagram generation HTTP API
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    get_visual_knowledge_service,
    get_s3_document_client,
)
from backend.application.services.visual_knowledge_service import VisualKnowledgeService
from backend.boundary.aws.s3_client import S3DocumentClient
from backend.boundary.db import get_async_db
from backend.boundary.db.CRUD.image_crud import image_crud
from backend.models.visual_knowledge import (
    ConceptBranchResponse,
    VisualKnowledgeRequest,
    VisualKnowledgeResponseModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["visual-knowledge"])


@router.post(
    "/{session_id}/visual-knowledge",
    response_model=VisualKnowledgeResponseModel,
    status_code=200,
)
async def generate_visual_knowledge(
    session_id: str,
    request: VisualKnowledgeRequest,
    visual_knowledge_service: VisualKnowledgeService = Depends(get_visual_knowledge_service),
) -> VisualKnowledgeResponseModel:
    """Generate on-demand visual knowledge diagram for an assistant message.

    Creates a detailed, branded concept diagram from an AI response with:
    1. Document expansion (RAG) - retrieve context from uploaded documents
    2. Concept curation (LLM) - extract main concepts and explorable branches
    3. Diagram generation (Gemini) - render high-quality visual with brand styling
    4. S3 persistence - store in S3 for efficient retrieval and long-term storage

    The diagram features:
    - Warm academic aesthetic (deep ink text, golden amber accents, warm cream background)
    - Detail-oriented design with 20+ visual elements for learning retention
    - Semantic visual hierarchy and connections
    - Stored persistently in S3 with session+image linking for chat history

    Request body:
    - ai_answer: The assistant response text to visualize

    Response:
    - s3_key: S3 object key for the diagram (e.g., sessions/{session_id}/images/{uuid}.png)
    - image_id: UUID of the persisted image record in database
    - mime_type: Detected image format ("image/png" or "image/jpeg")
    - main_concepts: 2-3 core topics extracted during curation
    - branches: 4-6 explorable concepts with id, label, 15-30 word description
    - image_generation_prompt: Full Gemini prompt (for auditability and regeneration)

    Args:
        session_id: Session ID to link image to session and chat history
        request: Visual knowledge request with ai_answer
        visual_knowledge_service: Injected service with 4-node LangGraph orchestrator

    Returns:
        VisualKnowledgeResponseModel: S3 key, image ID, MIME type, and extracted metadata

    Raises:
        HTTPException(400): Invalid input (empty ai_answer or invalid session_id)
        HTTPException(500): Generation failed at any pipeline stage (expansion, curation, generation, or S3 upload)
    """
    try:
        result = await visual_knowledge_service.generate(
            session_id=session_id,
            ai_answer=request.ai_answer,
        )
        return result
    except ValueError as e:
        logger.error(f"{__name__}:generate_visual_knowledge - ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"{__name__}:generate_visual_knowledge - {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{session_id}/images",
    response_model=list[VisualKnowledgeResponseModel],
    status_code=200,
)
async def get_session_images(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    s3_client: S3DocumentClient = Depends(get_s3_document_client),
) -> list[VisualKnowledgeResponseModel]:
    """Retrieve all visual knowledge images for a session.

    Used when resuming a session to load previously generated diagrams.
    Generates fresh presigned URLs for each image to ensure they're valid.

    Response:
    - Returns list of all images for the session, newest first
    - Each image includes presigned URL for direct S3 access
    - Presigned URLs valid for 1 hour from generation

    Args:
        session_id: Session UUID to retrieve images for
        db: Async database session (injected)
        s3_client: S3 client for presigned URL generation (injected)

    Returns:
        list[VisualKnowledgeResponseModel]: All images for the session with presigned URLs

    Raises:
        HTTPException(400): Invalid session_id format
    """
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    try:
        logger.info(f"{__name__}:get_session_images - START session_id={session_id}")

        # Retrieve all images for this session (newest first)
        images = await image_crud.get_by_session_id(db, session_uuid)

        logger.info(
            f"{__name__}:get_session_images - Retrieved {len(images)} images for session"
        )

        # Convert to response models with fresh presigned URLs
        responses = []
        for image in images:
            presigned_url, expires_at = s3_client.generate_presigned_download_url(
                s3_key=image.s3_key,
                expires_in=3600,
            )

            responses.append(
                VisualKnowledgeResponseModel(
                    s3_key=image.s3_key,
                    presigned_url=presigned_url,
                    expires_at=expires_at.isoformat(),
                    mime_type=image.mime_type,
                    main_concepts=image.main_concepts,
                    branches=[
                        ConceptBranchResponse(**branch) for branch in image.branches
                    ],
                    image_generation_prompt=image.image_generation_prompt,
                )
            )

        logger.info(f"{__name__}:get_session_images - END returning {len(responses)} images")
        return responses

    except Exception as e:
        logger.error(f"{__name__}:get_session_images - {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
