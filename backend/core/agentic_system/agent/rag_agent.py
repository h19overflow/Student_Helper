"""
RAG Q&A agent implementation.

Agent for answering questions with citations using FAISSStore retrieval.
Uses LangChain v1 create_agent with structured output.

Dependencies: langchain.agents, langchain_aws, backend.boundary.vdb
System role: RAG Q&A agent orchestration
"""

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse

from backend.boundary.vdb.faiss_store import FAISSStore
from backend.core.agentic_system.agent.rag_agent_prompt import get_rag_prompt
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse
from backend.core.agentic_system.agent.rag_agent_tool import create_search_tool


class RAGAgent:
    """
    RAG Q&A agent with citation support.

    Uses LangChain create_agent with FAISSStore for retrieval
    and returns structured responses with citations.
    """

    def __init__(
        self,
        vector_store: FAISSStore,
        model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        region: str = "ap-southeast-2",
        temperature: float = 0.0,
    ) -> None:
        """
        Initialize RAG agent with vector store and model.

        Args:
            vector_store: FAISSStore instance for retrieval
            model_id: Bedrock model identifier
            region: AWS region for Bedrock
            temperature: Model temperature (0.0 for deterministic)
        """
        self._vector_store = vector_store

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

    def invoke(self, question: str, session_id: str | None = None) -> RAGResponse:
        """
        Answer a question using RAG retrieval.

        Args:
            question: User's question
            session_id: Optional session ID for filtering

        Returns:
            RAGResponse: Structured response with answer and citations
        """
        prompt = get_rag_prompt()

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
        prompt = get_rag_prompt()

        context = await self._search_tool.ainvoke({"query": question, "k": 5})

        messages = prompt.invoke({
            "context": context,
            "question": question,
        }).to_messages()

        result = await self._agent.ainvoke({"messages": messages})

        return result["structured_response"]
