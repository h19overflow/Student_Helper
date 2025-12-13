"""
Diagram domain models and schemas.

Request/response schemas for Mermaid diagram generation.

Dependencies: pydantic
System role: Diagram API contracts
"""

from pydantic import BaseModel, Field
from backend.models.citation import Citation


class DiagramRequest(BaseModel):
    """Request schema for diagram generation."""

    prompt: str = Field(description="Diagram generation prompt")


class DiagramCitation(Citation):
    """Extended citation for diagram grounding."""

    claim: str = Field(description="Claim or statement being cited")


class DiagramResponse(BaseModel):
    """Response schema for diagram generation."""

    mermaid_code: str = Field(description="Generated Mermaid diagram code")
    citations: list[DiagramCitation] = Field(description="Grounding citations")
