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


def curation_node(
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

        # Format expanded docs for prompt
        docs_text = "\n".join(
            [
                f"---\n{doc.metadata.source_uri}\n{doc.content}\n---"
                for doc in state["expanded_docs"]
            ]
        )

        # Get prompt template and format
        prompt = get_visual_knowledge_prompt()
        messages = prompt.format_messages(expanded_docs=docs_text)

        # Invoke curation agent with structured output
        logger.debug(f"{__name__}:curation_node - Invoking curation agent")
        result = curation_agent.invoke({"messages": messages})

        # Extract structured response
        curation_result = result.get("structured_response")
        if not curation_result:
            raise ValueError("Curation agent did not return structured_response")

        logger.info(
            f"{__name__}:curation_node - END "
            f"concepts={len(curation_result.main_concepts)}, "
            f"branches={len(curation_result.branches)}"
        )

        return {
            "main_concepts": curation_result.main_concepts,
            "branches": curation_result.branches,
            "image_generation_prompt": curation_result.image_generation_prompt,
        }

    except Exception as e:
        logger.error(f"{__name__}:curation_node - {type(e).__name__}: {e}")
        return {"error": str(e)}
