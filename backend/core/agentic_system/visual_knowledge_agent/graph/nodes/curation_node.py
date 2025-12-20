"""Concept curation node for visual knowledge pipeline.

Extracts main concepts and branches from expanded documents using LLM agent.

Dependencies: logging, curation_agent, visual_knowledge_prompt, schema
System role: Second stage of LangGraph pipeline
"""

import logging
from typing import TYPE_CHECKING

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_prompt import (
    get_visual_knowledge_prompt,
)
from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    VisualKnowledgeState,
)

if TYPE_CHECKING:
    from backend.core.agentic_system.agent.rag_agent import RAGAgent

logger = logging.getLogger(__name__)


async def curation_node(
    state: VisualKnowledgeState,
    curation_agent: "RAGAgent",
) -> dict:
    """Extract concepts and create image generation prompt.

    Uses LLM agent to curate expanded docs into structured output:
    - main_concepts: 2-3 core topics
    - branches: 4-6 explorable sub-topics
    - image_generation_prompt: Detailed Gemini instruction

    Args:
        state: LangGraph state with expanded_docs
        curation_agent: LangChain agent with create_agent + ToolStrategy

    Returns:
        dict: State update with main_concepts, branches, prompt or error
    """
    try:
        logger.info(
            f"{__name__}:curation_node - START "
            f"expanded_docs={len(state['expanded_docs'])}"
        )

        # Step 1: Format expanded docs for prompt
        try:
            docs_text = "\n".join(
                [
                    f"---\n{doc.metadata.source_uri}\n{doc.content}\n---"
                    for doc in state["expanded_docs"]
                ]
            )
            logger.debug(f"{__name__}:curation_node - Formatted {len(state['expanded_docs'])} docs")
        except Exception as e:
            logger.error(
                f"{__name__}:curation_node - FAILED at docs_text formatting - "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            raise

        # Step 2: Get prompt template and format
        try:
            prompt = get_visual_knowledge_prompt()
            messages = prompt.format_messages(expanded_docs=docs_text)
            logger.debug(f"{__name__}:curation_node - Prompt formatted with messages")
        except Exception as e:
            logger.error(
                f"{__name__}:curation_node - FAILED at prompt formatting - "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            raise

        # Step 3: Invoke curation agent with structured output
        try:
            logger.debug(f"{__name__}:curation_node - Invoking curation agent")
            result = await curation_agent.ainvoke({"messages": messages})
            logger.info(f"{__name__}:curation_node - Agent invoked successfully")
        except Exception as e:
            logger.error(
                f"{__name__}:curation_node - FAILED at agent.invoke - "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            raise

        # Step 4: Extract structured response
        try:
            logger.debug(
                f"{__name__}:curation_node - Agent result type: {type(result).__name__}, "
                f"keys: {result.keys() if isinstance(result, dict) else 'N/A'}"
            )
            curation_result = result.get("structured_response") if isinstance(result, dict) else result
            logger.info(f"{__name__}:curation_node - Extracted structured_response")
        except Exception as e:
            logger.error(
                f"{__name__}:curation_node - FAILED at extracting structured_response - "
                f"{type(e).__name__}: {e}. Result type: {type(result).__name__}",
                exc_info=True
            )
            raise

        # Step 5: Validate curation result
        try:
            if not curation_result:
                raise ValueError("structured_response is None or empty")
            logger.debug(
                f"{__name__}:curation_node - Curation result type: {type(curation_result).__name__}"
            )
        except Exception as e:
            logger.error(
                f"{__name__}:curation_node - FAILED at validation - "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )
            raise

        # Step 6: Extract fields from curation result
        try:
            main_concepts = curation_result.main_concepts
            branches = curation_result.branches
            image_prompt = curation_result.image_generation_prompt
            logger.info(
                f"{__name__}:curation_node - END "
                f"concepts={len(main_concepts)}, branches={len(branches)}"
            )
        except Exception as e:
            logger.error(
                f"{__name__}:curation_node - FAILED at extracting fields from result - "
                f"{type(e).__name__}: {e}. Result: {curation_result}",
                exc_info=True
            )
            raise

        return {
            "main_concepts": main_concepts,
            "branches": branches,
            "image_generation_prompt": image_prompt,
        }

    except Exception as e:
        logger.error(
            f"{__name__}:curation_node - FINAL ERROR - "
            f"{type(e).__name__}: {str(e)[:200]}",
            exc_info=True
        )
        return {"error": str(e)}
