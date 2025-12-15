"""
RAG agent system prompt.

Defines the system prompt template for the RAG Q&A agent.
Instructs agent on citation usage and answer formatting.
Supports Langfuse prompt registry integration.

Dependencies: langchain_core.prompts, backend.observability.prompt_registry
System role: Prompt template for RAG agent behavior
"""

import logging

from langchain_core.prompts import ChatPromptTemplate

from backend.observability.prompt_registry.models import ModelConfig
from backend.observability.prompt_registry.registry import PromptRegistry

logger = logging.getLogger(__name__)

RAG_PROMPT_NAME = "rag-qa-agent"

SYSTEM_PROMPT = """You are a helpful study assistant that answers questions based on provided context.

## Instructions
1. Use ONLY the provided context to answer questions
2. If the context doesn't contain enough information, say so clearly
3. Always cite your sources using the chunk_id from the context
4. Be concise but thorough in your explanations
5. If multiple sources support your answer, cite all of them

## Conversation History
If provided, recent conversation history shows context for the current question.
Use this to:
- Understand follow-up questions that reference previous messages
- Maintain conversational coherence
- Avoid repeating information already discussed

## Context Format
Each context chunk includes:
- content: The actual text content use this for citation
- page: Page number (if available) use this for citation
- section: Section heading (if available) use this for citation
- source_uri: Original document location
- relevance_score: How relevant this chunk is to the query

## Response Guidelines
- Answer the question directly and accurately
- Include relevant citations for each claim you make
- Set confidence based on how well the context covers the question
- Briefly explain your reasoning process"""

RAG_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """{chat_history}

Context:
{context}

Question: {question}

Please provide a well-cited answer based on the context above."""),
])


def register_rag_prompt(
    model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    temperature: float = 0.0,
    labels: list[str] | None = None,
) -> None:
    """
    Register RAG agent prompt with Langfuse.

    Args:
        model_id: Bedrock model identifier
        temperature: Model temperature
        labels: Optional labels (e.g., ["production", "staging"])
    """
    registry = PromptRegistry()

    if not registry.is_enabled:
        logger.debug("Prompt registry disabled, skipping registration")
        return

    config = ModelConfig(
        model=model_id,
        temperature=temperature,
    )

    registry.register_prompt(
        name=RAG_PROMPT_NAME,
        template=RAG_AGENT_PROMPT,
        config=config,
        labels=labels or ["development"],
    )
    logger.info("Registered RAG prompt: name=%s", RAG_PROMPT_NAME)


def get_rag_prompt(
    use_registry: bool = False,
    label: str | None = None,
) -> ChatPromptTemplate:
    """
    Get the RAG agent prompt template.

    Args:
        use_registry: Whether to fetch from Langfuse registry
        label: Optional label filter when using registry

    Returns:
        ChatPromptTemplate: Configured prompt for RAG agent
    """
    if use_registry:
        registry = PromptRegistry()
        if registry.is_enabled:
            prompt = registry.get_langchain_prompt(RAG_PROMPT_NAME, label=label)
            if prompt is not None:
                logger.debug("Using prompt from registry: name=%s", RAG_PROMPT_NAME)
                return prompt
            logger.debug("Prompt not found in registry, using local template")

    return RAG_AGENT_PROMPT
