"""
RAG Q&A agent implementation.

Agent for answering questions with citations using S3VectorsStore retrieval.
Uses LangChain v1 create_agent with structured output.
Supports Langfuse prompt registry integration for versioned prompts.
Supports streaming via astream() method for WebSocket chat.

Dependencies: langchain.agents, langchain_aws, backend.boundary.vdb
System role: RAG Q&A agent orchestration
"""

from collections.abc import AsyncGenerator

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage

from backend.boundary.vdb.s3_vectors_store import S3VectorsStore
from backend.core.agentic_system.agent.rag_agent_prompt import (
    get_rag_prompt,
    register_rag_prompt,
)
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse
from backend.core.agentic_system.agent.rag_agent_tool import create_search_tool
from backend.models.streaming import StreamEvent, StreamEventType, StreamingCitation


class RAGAgent:
    """
    RAG Q&A agent with citation support.

    Uses LangChain create_agent with S3VectorsStore for retrieval
    and returns structured responses with citations.
    Supports Langfuse prompt registry for versioned prompt management.
    """

    def __init__(
        self,
        vector_store: S3VectorsStore,
        model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        region: str = "ap-southeast-2",
        temperature: float = 0.0,
        use_prompt_registry: bool = False,
        prompt_label: str | None = None,
    ) -> None:
        """
        Initialize RAG agent with vector store and model.

        Args:
            vector_store: S3VectorsStore instance for retrieval
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

    def invoke(
        self,
        question: str,
        session_id: str | None = None,
        chat_history: list[BaseMessage] | None = None,
    ) -> RAGResponse:
        """
        Answer a question using RAG retrieval.

        Args:
            question: User's question
            session_id: Optional session ID for filtering
            chat_history: Optional conversation history for context

        Returns:
            RAGResponse: Structured response with answer and citations
        """
        prompt = get_rag_prompt(
            use_registry=self._use_prompt_registry,
            label=self._prompt_label,
        )

        context = self._search_tool.invoke({"query": question, "k": 5})

        # Format chat history if provided
        history_text = ""
        if chat_history:
            formatted_messages = [
                f"{'User' if msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in chat_history
            ]
            history_text = "Previous Conversation:\n" + "\n".join(formatted_messages) + "\n"

        messages = prompt.invoke({
            "context": context,
            "question": question,
            "chat_history": history_text,
        }).to_messages()

        result = self._agent.invoke({"messages": messages})

        return result["structured_response"]

    async def ainvoke(
        self,
        question: str,
        session_id: str | None = None,
        chat_history: list[BaseMessage] | None = None,
    ) -> RAGResponse:
        """
        Async version of invoke.

        Args:
            question: User's question
            session_id: Optional session ID for filtering
            chat_history: Optional conversation history for context

        Returns:
            RAGResponse: Structured response with answer and citations
        """
        prompt = get_rag_prompt(
            use_registry=self._use_prompt_registry,
            label=self._prompt_label,
        )

        context = await self._search_tool.ainvoke({"query": question, "k": 5})

        # Format chat history if provided
        history_text = ""
        if chat_history:
            formatted_messages = [
                f"{'User' if msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in chat_history
            ]
            history_text = "Previous Conversation:\n" + "\n".join(formatted_messages) + "\n"

        messages = prompt.invoke({
            "context": context,
            "question": question,
            "chat_history": history_text,
        }).to_messages()

        result = await self._agent.ainvoke({"messages": messages})

        return result["structured_response"]

    async def astream(
        self,
        question: str,
        session_id: str | None = None,
        chat_history: list[BaseMessage] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream response tokens for real-time chat.

        Retrieves context, extracts citations, then streams LLM tokens.
        Unlike ainvoke(), does not use structured output agent.

        Args:
            question: User's question
            session_id: Optional session ID for filtering
            chat_history: Optional conversation history for context

        Yields:
            StreamEvent: Context, token, citations, and complete events
        """
        # 1. Retrieve context directly from vector store
        # Note: session_id filter disabled for now to allow cross-session search
        # TODO: Re-enable when document indexing properly associates session_ids
        search_results = self._vector_store.similarity_search(
            query=question,
            k=5,
            # session_id=session_id,  # Disabled: causes empty results if session has no docs
        )

        # 2. Extract citations from search results
        citations = [
            StreamingCitation(
                chunk_id=result.chunk_id,
                doc_name=result.metadata.source_uri.split("/")[-1] if result.metadata.source_uri else "unknown",
                page=result.metadata.page,
                section=result.metadata.section,
                source_uri=result.metadata.source_uri,
            )
            for result in search_results
        ]

        # 3. Yield context event with citation metadata
        yield StreamEvent(
            event=StreamEventType.CONTEXT,
            data={
                "chunks": [
                    {
                        "chunk_id": result.chunk_id,
                        "content_snippet": result.content[:200],
                        "page": result.metadata.page,
                        "section": result.metadata.section,
                        "source_uri": result.metadata.source_uri,
                        "relevance_score": result.similarity_score,
                    }
                    for result in search_results
                ]
            },
        )

        # 4. Format context for prompt
        if not search_results:
            context_text = "No relevant documents found."
        else:
            formatted_chunks = []
            for result in search_results:
                chunk_text = f"""---
chunk_id: {result.chunk_id}
page: {result.metadata.page}
section: {result.metadata.section}
source_uri: {result.metadata.source_uri}
relevance_score: {result.similarity_score:.3f}

{result.content}
---"""
                formatted_chunks.append(chunk_text)
            context_text = "\n".join(formatted_chunks)

        # 5. Format chat history
        history_text = ""
        if chat_history:
            formatted_messages = [
                f"{'User' if msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in chat_history
            ]
            history_text = "Previous Conversation:\n" + "\n".join(formatted_messages) + "\n"

        # 6. Build prompt messages
        prompt = get_rag_prompt(
            use_registry=self._use_prompt_registry,
            label=self._prompt_label,
        )
        messages = prompt.invoke({
            "context": context_text,
            "question": question,
            "chat_history": history_text,
        }).to_messages()

        # 7. Stream tokens from model
        full_answer = ""
        token_index = 0
        async for chunk in self._model.astream(messages):
            if chunk.content:
                # Handle both string and list content from Bedrock
                if isinstance(chunk.content, list):
                    # If content is a list of items, convert to string
                    token_content = "".join(
                        str(item) if isinstance(item, str) else (item.get("text", "") if isinstance(item, dict) else str(item))
                        for item in chunk.content
                    )
                else:
                    # If content is already a string
                    token_content = str(chunk.content)

                full_answer += token_content
                yield StreamEvent(
                    event=StreamEventType.TOKEN,
                    data={"token": token_content, "index": token_index},
                )
                token_index += 1

        # 8. Yield citations
        yield StreamEvent(
            event=StreamEventType.CITATIONS,
            data={
                "citations": [citation.model_dump() for citation in citations]
            },
        )

        # 9. Yield completion event
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "Sending completion event",
            extra={
                "full_answer_length": len(full_answer),
                "full_answer_preview": full_answer[:100] if full_answer else "EMPTY",
            },
        )
        yield StreamEvent(
            event=StreamEventType.COMPLETE,
            data={"fullAnswer": full_answer},
        )


if __name__ == "__main__":
    from backend.boundary.vdb.s3_vectors_store import S3VectorsStore

    vector_store = S3VectorsStore()
    agent = RAGAgent(vector_store)
    result = agent.invoke("What does hamza do , and how many projects does he have?")
    print(result)