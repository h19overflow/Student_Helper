"""Visual knowledge API request/response models.

Defines Pydantic DTOs for API contracts.

Dependencies: pydantic, uuid
System role: API data models for visual knowledge endpoints
"""

from pydantic import BaseModel, Field


class VisualKnowledgeRequest(BaseModel):
    """Request to generate visual knowledge diagram.

    User sends the assistant's response text to be visualized.
    """

    ai_answer: str = Field(
        min_length=1,
        description="The assistant response to visualize as a diagram",
    )


class ConceptBranchResponse(BaseModel):
    """A branch concept in the visual diagram.

    Represents an explorable sub-topic that users can click to learn more.
    """

    id: str = Field(description="Unique identifier for the branch")
    label: str = Field(description="Human-readable label (e.g., 'Activation Functions')")
    description: str = Field(
        description="10-20 word description of what users will learn"
    )


class VisualKnowledgeResponseModel(BaseModel):
    """Response with visual knowledge diagram and metadata.

    Contains the generated diagram image and extracted concepts.
    """

    image_base64: str = Field(
        description="Base64-encoded PNG diagram image for inline display"
    )
    mime_type: str = Field(
        default="image/png",
        description="MIME type of the image (always image/png)",
    )
    main_concepts: list[str] = Field(
        description="2-3 core topics extracted from the diagram"
    )
    branches: list[ConceptBranchResponse] = Field(
        description="4-6 explorable branches with IDs and descriptions"
    )
    image_generation_prompt: str = Field(
        description="The prompt sent to Gemini (for transparency/debugging)"
    )
