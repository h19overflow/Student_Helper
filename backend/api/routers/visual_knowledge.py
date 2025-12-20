"""Visual Knowledge diagram generation endpoints.

Routes:
- POST /sessions/{session_id}/visual-knowledge - Generate visual knowledge diagram from AI response

Dependencies: backend.application.services.visual_knowledge_service
System role: Visual knowledge diagram generation HTTP API
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_visual_knowledge_service
from backend.application.services.visual_knowledge_service import VisualKnowledgeService
from backend.models.visual_knowledge import (
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
