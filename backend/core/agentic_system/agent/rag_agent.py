"""
RAG Q&A agent implementation.

Agent for answering questions with citations using S3VectorsStore retrieval.
Uses LangChain v1 create_agent with structured output.
Supports Langfuse prompt registry integration for versioned prompts.
Supports streaming via astream() method for WebSocket chat.

Dependencies: langchain.agents, langchain_aws, backend.boundary.vdb
System role: RAG Q&A agent orchestration
"""

import logging
from collections.abc import AsyncGenerator

from fastapi.concurrency import run_in_threadpool
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage

from backend.boundary.vdb.vector_store_factory import get_vector_store
from backend.core.agentic_system.agent.rag_agent_prompt import (
    get_rag_prompt,
    register_rag_prompt,
)
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse
from backend.core.agentic_system.agent.rag_agent_tool import create_search_tool
from backend.models.streaming import StreamEvent, StreamEventType, StreamingCitation
from langchain_google_genai import ChatGoogleGenerativeAI
logger = logging.getLogger(__name__)


class RAGAgent:
    """
    RAG Q&A agent with citation support.

    Uses LangChain create_agent with S3VectorsStore for retrieval
    and returns structured responses with citations.
    Supports Langfuse prompt registry for versioned prompt management.
    """

    def __init__(
        self,
        vector_store=None,
        model_id: str = "gemini-3-flash-preview",
        region: str = "ap-southeast-2",
        temperature: float = 0.0,
        use_prompt_registry: bool = False,
        prompt_label: str | None = None,
    ) -> None:
        """
        Initialize RAG agent with vector store and model.

        Args:
            vector_store: Vector store instance (FAISS or S3Vectors). If None, uses factory.
            model_id: Bedrock model identifier
            region: AWS region for Bedrock
            temperature: Model temperature (0.0 for deterministic)
            use_prompt_registry: Whether to fetch prompts from Langfuse
            prompt_label: Optional label filter when using registry
        """
        # Use factory to select vector store based on environment if not provided
        if vector_store is None:
            vector_store = get_vector_store()
        self._vector_store = vector_store
        self._use_prompt_registry = use_prompt_registry
        self._prompt_label = prompt_label
        self._model_id = model_id
        self._temperature = temperature

        # Initialize streaming model (used by astream method)
        self._model = ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
        )

        self._search_tool = create_search_tool(vector_store)

        self._agent = create_agent(
            model="google_genai:gemini-3-flash-preview",
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
        logger.info(f"{__name__}:astream - START session_id={session_id}, question_len={len(question)}")

        # Step 1: Retrieve context from vector store
        try:
            logger.info(f"{__name__}:astream - Step 1: Calling similarity_search (k=5)")
            search_results = await run_in_threadpool(
                self._vector_store.similarity_search,
                query=question,
                k=5,
                session_id=session_id,
            )
            logger.info(f"{__name__}:astream - Step 1 OK: Retrieved {len(search_results)} chunks")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 1 FAILED: similarity_search - {type(e).__name__}: {e}")
            raise

        # Step 2: Extract citations from search results
        try:
            logger.info(f"{__name__}:astream - Step 2: Extracting citations")
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
            logger.info(f"{__name__}:astream - Step 2 OK: Extracted {len(citations)} citations")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 2 FAILED: citation extraction - {type(e).__name__}: {e}")
            raise

        # Step 3: Yield context event with citation metadata
        try:
            logger.info(f"{__name__}:astream - Step 3: Yielding CONTEXT event")
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
            logger.info(f"{__name__}:astream - Step 3 OK: CONTEXT event yielded")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 3 FAILED: CONTEXT event - {type(e).__name__}: {e}")
            raise

        # Step 4: Format context for prompt
        try:
            logger.info(f"{__name__}:astream - Step 4: Formatting context for prompt")
            if not search_results:
                context_text = "No relevant documents found."
                logger.warning(f"{__name__}:astream - No search results, using fallback context")
            else:
                formatted_chunks = []
                for result in search_results:
                    page_info = f"Page {result.metadata.page}" if result.metadata.page else "Page unknown"
                    section_info = f", Section: {result.metadata.section}" if result.metadata.section else ""
                    chunk_text = f"""---
[{page_info}{section_info}]

{result.content}
---"""
                    formatted_chunks.append(chunk_text)
                context_text = "\n".join(formatted_chunks)
            logger.info(f"{__name__}:astream - Step 4 OK: context_len={len(context_text)}")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 4 FAILED: context formatting - {type(e).__name__}: {e}")
            raise

        # Step 5: Format chat history
        try:
            logger.info(f"{__name__}:astream - Step 5: Formatting chat history")
            history_text = ""
            if chat_history:
                formatted_messages = [
                    f"{'User' if msg.type == 'human' else 'Assistant'}: {msg.content}"
                    for msg in chat_history
                ]
                history_text = "Previous Conversation:\n" + "\n".join(formatted_messages) + "\n"
            logger.info(f"{__name__}:astream - Step 5 OK: history_len={len(history_text)}, msg_count={len(chat_history) if chat_history else 0}")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 5 FAILED: history formatting - {type(e).__name__}: {e}")
            raise

        # Step 6: Build prompt messages
        try:
            logger.info(f"{__name__}:astream - Step 6: Building prompt messages")
            prompt = get_rag_prompt(
                use_registry=self._use_prompt_registry,
                label=self._prompt_label,
            )
            messages = prompt.invoke({
                "context": context_text,
                "question": question,
                "chat_history": history_text,
            }).to_messages()
            logger.info(f"{__name__}:astream - Step 6 OK: Built {len(messages)} messages")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 6 FAILED: prompt building - {type(e).__name__}: {e}")
            raise

        # Step 7: Stream tokens from model
        full_answer = ""
        token_index = 0
        try:
            logger.info(f"{__name__}:astream - Step 7: Starting LLM stream (model={self._model_id})")
            async for chunk in self._model.astream(messages):
                if chunk.content:
                    # Handle both string and list content from Bedrock
                    if isinstance(chunk.content, list):
                        token_content = "".join(
                            str(item) if isinstance(item, str) else (item.get("text", "") if isinstance(item, dict) else str(item))
                            for item in chunk.content
                        )
                    else:
                        token_content = str(chunk.content)

                    full_answer += token_content
                    yield StreamEvent(
                        event=StreamEventType.TOKEN,
                        data={"token": token_content, "index": token_index},
                    )
                    token_index += 1

                    # Log first few tokens for debugging
                    if token_index <= 3:
                        logger.info(f"{__name__}:astream - Token #{token_index}: '{token_content[:50]}'")

            logger.info(f"{__name__}:astream - Step 7 OK: Streamed {token_index} tokens, answer_len={len(full_answer)}")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 7 FAILED: LLM streaming - {type(e).__name__}: {e}")
            raise

        # Step 8: Yield citations
        try:
            logger.info(f"{__name__}:astream - Step 8: Yielding CITATIONS event")
            yield StreamEvent(
                event=StreamEventType.CITATIONS,
                data={
                    "citations": [citation.model_dump() for citation in citations]
                },
            )
            logger.info(f"{__name__}:astream - Step 8 OK: CITATIONS event yielded")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 8 FAILED: CITATIONS event - {type(e).__name__}: {e}")
            raise

        # Step 9: Yield completion event
        try:
            logger.info(f"{__name__}:astream - Step 9: Yielding COMPLETE event (answer_len={len(full_answer)})")
            yield StreamEvent(
                event=StreamEventType.COMPLETE,
                data={"full_answer": full_answer},
            )
            logger.info(f"{__name__}:astream - Step 9 OK: COMPLETE event yielded")
        except Exception as e:
            logger.error(f"{__name__}:astream - Step 9 FAILED: COMPLETE event - {type(e).__name__}: {e}")
            raise

        logger.info(f"{__name__}:astream - END session_id={session_id}")


