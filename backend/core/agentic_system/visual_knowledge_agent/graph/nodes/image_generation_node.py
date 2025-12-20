"""Image generation node for visual knowledge pipeline.

Calls Google Gemini to generate diagram images based on curation prompt.

Dependencies: logging, base64, google.genai, schema
System role: Third stage of LangGraph pipeline
"""

import base64
import logging
from typing import TYPE_CHECKING

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    VisualKnowledgeState,
)

if TYPE_CHECKING:
    from google import genai

logger = logging.getLogger(__name__)


def image_generation_node(
    state: VisualKnowledgeState,
    google_client: "genai.Client",
) -> dict:
    """Generate diagram image via Google Gemini.

    Calls gemini-3-pro-image-preview to generate diagram based on
    image_generation_prompt from curation. Extracts and base64-encodes image.

    Args:
        state: LangGraph state with image_generation_prompt
        google_client: Google Generative AI client

    Returns:
        dict: State update with image_base64, mime_type or error
    """
    try:
        logger.info(
            f"{__name__}:image_generation_node - START "
            f"prompt_len={len(state['image_generation_prompt'])}"
        )

        # Call Gemini image generation
        logger.debug(f"{__name__}:image_generation_node - Calling Gemini API")
        response = google_client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=state["image_generation_prompt"],
        )

        # Extract image from response (nano_trial.py pattern)
        logger.debug(f"{__name__}:image_generation_node - Extracting image from response")
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_data = part.inline_data
                    image_base64 = base64.b64encode(image_data.data).decode("utf-8")

                    logger.info(
                        f"{__name__}:image_generation_node - END "
                        f"image_len={len(image_base64)}, mime_type={image_data.mime_type}"
                    )

                    return {
                        "image_base64": image_base64,
                        "mime_type": image_data.mime_type,
                    }

        raise ValueError("No image data found in Gemini response")

    except Exception as e:
        logger.error(f"{__name__}:image_generation_node - {type(e).__name__}: {e}")
        return {"error": str(e)}
