"""Visual knowledge agent schemas and prompts.

Exports schema definitions and prompt templates for curation agent.
"""

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    ConceptBranch,
    CurationResult,
    VisualKnowledgeResponse,
    VisualKnowledgeState,
)

__all__ = [
    "ConceptBranch",
    "CurationResult",
    "VisualKnowledgeResponse",
    "VisualKnowledgeState",
]
