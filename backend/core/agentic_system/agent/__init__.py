"""
RAG Q&A agent module.

Provides RAG agent for answering questions with citations.
Supports Langfuse prompt registry integration.

Dependencies: langchain, langchain_aws, backend.boundary.vdb
System role: Agent module exports
"""

from backend.core.agentic_system.agent.rag_agent import RAGAgent
from backend.core.agentic_system.agent.rag_agent_prompt import register_rag_prompt
from backend.core.agentic_system.agent.rag_agent_schema import RAGCitation, RAGResponse

__all__ = ["RAGAgent", "RAGResponse", "RAGCitation", "register_rag_prompt"]
