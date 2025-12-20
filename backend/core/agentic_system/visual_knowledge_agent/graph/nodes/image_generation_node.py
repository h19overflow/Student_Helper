"""Image generation node for visual knowledge pipeline.

Calls Google Gemini to generate diagram images based on curation prompt.

Dependencies: logging, asyncio, base64, google.genai, schema
System role: Third stage of LangGraph pipeline
"""

import asyncio
import base64
import logging
from typing import TYPE_CHECKING

from backend.core.agentic_system.visual_knowledge_agent.agent.image_generation_prompt import (
    get_image_generation_system_prompt,
)
from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    VisualKnowledgeState,
)

if TYPE_CHECKING:
    from google import genai

logger = logging.getLogger(__name__)


async def image_generation_node(
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
        # Step 1: Validate input state
        try:
            prompt = state["image_generation_prompt"]
            logger.info(
                f"{__name__}:image_generation_node - START "
                f"prompt_len={len(prompt)}"
            )
        except Exception as e:
            logger.error(
                f"{__name__}:image_generation_node - FAILED at state validation - "
                f"{type(e).__name__}: {e}. Available keys: {state.keys()}",
                exc_info=True
            )
            raise

        # Step 2: Call Gemini image generation with brand system prompt
        try:
            logger.debug(f"{__name__}:image_generation_node - Calling Gemini API")
            system_prompt = get_image_generation_system_prompt()

            # Prepend system prompt to user prompt for better output quality
            full_prompt = f"{system_prompt}\n\nUSER REQUEST:\n{prompt}"

            response = await asyncio.to_thread(
                google_client.models.generate_content,
                model="gemini-3-pro-image-preview",
                contents=full_prompt,
            )
            logger.info(f"{__name__}:image_generation_node - Gemini API called successfully")
        except Exception as e:
            logger.error(
                f"{__name__}:image_generation_node - FAILED at Gemini API call - "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            raise

        # Step 3: Extract image from response
        try:
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
            logger.error(
                f"{__name__}:image_generation_node - FAILED at image extraction - "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            raise

    except Exception as e:
        logger.error(
            f"{__name__}:image_generation_node - FINAL ERROR - "
            f"{type(e).__name__}: {str(e)[:200]}",
            exc_info=True
        )
        return {"error": str(e)}
