"""
RAGAS evaluation scores model.

Data class for RAGAS (RAG Assessment) evaluation results.
"""

from dataclasses import dataclass


@dataclass
class RagasScores:
    """RAGAS evaluation scores.
    
    All scores are normalized to 0-1 range.
    
    Attributes:
        faithfulness: Answer is grounded in retrieved context
        answer_relevance: Answer addresses the question
        context_recall: Retrieved context contains answer-supporting info
        context_precision: Retrieved context is relevant
    """

    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    context_recall: float = 0.0
    context_precision: float = 0.0

    @property
    def average(self) -> float:
        """Average of all RAGAS scores."""
        scores = [
            self.faithfulness,
            self.answer_relevance,
            self.context_recall,
            self.context_precision,
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "faithfulness": round(self.faithfulness, 3),
            "answer_relevance": round(self.answer_relevance, 3),
            "context_recall": round(self.context_recall, 3),
            "context_precision": round(self.context_precision, 3),
            "average": round(self.average, 3),
        }
