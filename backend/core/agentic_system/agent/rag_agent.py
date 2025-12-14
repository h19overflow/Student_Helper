"""
RAG Q&A agent implementation.

Agent for answering questions with citations using FAISSStore retrieval.
Uses LangChain v1 create_agent with structured output.
Supports Langfuse prompt registry integration for versioned prompts.

Dependencies: langchain.agents, langchain_aws, backend.boundary.vdb
System role: RAG Q&A agent orchestration
"""

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse

from backend.boundary.vdb.faiss_store import FAISSStore
from backend.core.agentic_system.agent.rag_agent_prompt import (
    get_rag_prompt,
    register_rag_prompt,
)
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse
from backend.core.agentic_system.agent.rag_agent_tool import create_search_tool


class RAGAgent:
    """
    RAG Q&A agent with citation support.

    Uses LangChain create_agent with FAISSStore for retrieval
    and returns structured responses with citations.
    Supports Langfuse prompt registry for versioned prompt management.
    """

    def __init__(
        self,
        vector_store: FAISSStore,
        model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        region: str = "ap-southeast-2",
        temperature: float = 0.0,
        use_prompt_registry: bool = False,
        prompt_label: str | None = None,
    ) -> None:
        """
        Initialize RAG agent with vector store and model.

        Args:
            vector_store: FAISSStore instance for retrieval
            model_id: Bedrock model identifier
            region: AWS region for Bedrock
            temperature: Model temperature (0.0 for deterministic)
            use_prompt_registry: Whether to fetch prompts from Langfuse
            prompt_label: Optional label filter when using registry
        """
        self._vector_store = vector_store
        self._use_prompt_registry = use_prompt_registry
        self._prompt_label = prompt_label
        self._model_id = model_id
        self._temperature = temperature

        self._model = ChatBedrockConverse(
            model=model_id,
            region_name=region,
            temperature=temperature,
        )

        self._search_tool = create_search_tool(vector_store)

        self._agent = create_agent(
            model=self._model,
            tools=[self._search_tool],
            response_format=ToolStrategy(RAGResponse),
        )

        if use_prompt_registry:
            register_rag_prompt(
                model_id=model_id,
                temperature=temperature,
                labels=[prompt_label] if prompt_label else None,
            )

    def invoke(self, question: str, session_id: str | None = None) -> RAGResponse:
        """
        Answer a question using RAG retrieval.

        Args:
            question: User's question
            session_id: Optional session ID for filtering

        Returns:
            RAGResponse: Structured response with answer and citations
        """
        prompt = get_rag_prompt(
            use_registry=self._use_prompt_registry,
            label=self._prompt_label,
        )

        context = self._search_tool.invoke({"query": question, "k": 5})

        messages = prompt.invoke({
            "context": context,
            "question": question,
        }).to_messages()

        result = self._agent.invoke({"messages": messages})

        return result["structured_response"]

    async def ainvoke(
        self,
        question: str,
        session_id: str | None = None,
    ) -> RAGResponse:
        """
        Async version of invoke.

        Args:
            question: User's question
            session_id: Optional session ID for filtering

        Returns:
            RAGResponse: Structured response with answer and citations
        """
        prompt = get_rag_prompt(
            use_registry=self._use_prompt_registry,
            label=self._prompt_label,
        )

        context = await self._search_tool.ainvoke({"query": question, "k": 5})

        messages = prompt.invoke({
            "context": context,
            "question": question,
        }).to_messages()

        result = await self._agent.ainvoke({"messages": messages})

        return result["structured_response"]
