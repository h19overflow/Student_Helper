"""Visual knowledge agent module for diagram generation.

Exports main agent class and schema for public use.
"""

from backend.core.agentic_system.visual_knowledge_agent.agent.visual_knowledge_schema import (
    ConceptBranch,
    CurationResult,
    VisualKnowledgeResponse,
    VisualKnowledgeState,
)
from backend.core.agentic_system.visual_knowledge_agent.visual_knowledge_agent import (
    VisualKnowledgeAgent,
)

__all__ = [
    "VisualKnowledgeAgent",
    "VisualKnowledgeResponse",
    "VisualKnowledgeState",
    "CurationResult",
    "ConceptBranch",
]
