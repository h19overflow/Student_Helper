"""Visual knowledge agent schemas for state management and responses.

This module defines:
- Pydantic models for structured agent responses
- TypedDict schema for LangGraph state management
- Data structures for concepts, branches, and visual diagrams

Dependencies: pydantic, typing, vector_schemas
System role: Data schemas for visual knowledge pipeline
"""

from typing import TypedDict

from pydantic import BaseModel, Field

from backend.boundary.vdb.vector_schemas import VectorSearchResult


class ConceptBranch(BaseModel):
    """Explorable concept from curation agent.

    Represents a sub-topic or branch that users can click to explore further.
    """

    id: str = Field(description="Unique identifier for the branch")
    label: str = Field(description="Human-readable label for the branch")
    description: str = Field(
        description="10-20 word description suitable for user exploration"
    )


class CurationResult(BaseModel):
    """Structured output from curation agent.

    Contains extracted concepts and detailed image generation prompt.
    """

    main_concepts: list[str] = Field(
        description="2-3 core topics extracted from documents"
    )
    branches: list[ConceptBranch] = Field(
        description="4-6 explorable sub-topics with descriptions"
    )
    image_generation_prompt: str = Field(
        description="Detailed instructions for Gemini image generation"
    )


class VisualKnowledgeResponse(BaseModel):
    """Final response with visual diagram and metadata.

    Contains base64-encoded image, concepts, branches, and generation prompt.
    """

    image_base64: str = Field(description="Base64-encoded PNG diagram image")
    mime_type: str = Field(
        default="image/png", description="MIME type of the image"
    )
    main_concepts: list[str] = Field(
        description="2-3 core concepts from the diagram"
    )
    branches: list[ConceptBranch] = Field(description="4-6 branches in the diagram")
    image_generation_prompt: str = Field(
        description="Prompt sent to Gemini for transparency/debugging"
    )


class VisualKnowledgeState(TypedDict, total=False):
    """LangGraph state schema for visual knowledge pipeline.

    Tracks data flow through document expansion, curation, and image generation.
    TypedDict with total=False allows optional fields for flexibility.
    """

    # Pipeline inputs
    ai_answer: str
    session_id: str | None

    # Document expansion output
    expanded_docs: list[VectorSearchResult]

    # Curation output
    main_concepts: list[str]
    branches: list[ConceptBranch]
    image_generation_prompt: str

    # Image generation output
    image_base64: str
    mime_type: str

    # Error tracking
    error: str | None
