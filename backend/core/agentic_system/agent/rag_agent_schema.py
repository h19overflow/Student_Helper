"""
RAG agent response schemas.

Defines structured output schema for RAG Q&A agent responses
including answer and source citations.

Dependencies: pydantic
System role: Agent response schema definitions
"""

from pydantic import BaseModel, Field


class RAGCitation(BaseModel):
    """Citation for a source chunk used in the answer."""

    chunk_id: str = Field(description="Unique chunk identifier")
    content_snippet: str = Field(description="Brief excerpt from source (first 100 chars)")
    page: int | None = Field(default=None, description="Page number in source document")
    section: str | None = Field(default=None, description="Section heading if available")
    source_uri: str = Field(description="Source document URI")
    relevance_score: float = Field(description="Retrieval similarity score (0.0-1.0)")


class RAGResponse(BaseModel):
    """Structured response from RAG Q&A agent."""

    answer: str = Field(description="Answer to the user's question based on context")
    citations: list[RAGCitation] = Field(
        default_factory=list,
        description="Citations to source documents used in the answer",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the answer (0.0-1.0)",
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of how the answer was derived",
    )
