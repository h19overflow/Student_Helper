"""
LLM Judge evaluation scores model.

Data class for LLM-as-Judge evaluation results.
"""

from dataclasses import dataclass


@dataclass
class JudgeScores:
    """LLM judge evaluation scores (0-10 scale).
    
    Attributes:
        relevance: Does answer address the question? (0-10)
        completeness: Does answer cover key points? (0-10)
        coherence: Is answer well-structured and clear? (0-10)
        hallucination_score: Inverse of hallucination (0=high, 10=none)
        overall_score: Overall quality score (0-10)
    """

    relevance: float = 0.0
    completeness: float = 0.0
    coherence: float = 0.0
    hallucination_score: float = 0.0  # 0=high hallucination, 10=no hallucination
    overall_score: float = 0.0

    @property
    def normalized_overall(self) -> float:
        """Overall score normalized to 0-1 range."""
        return self.overall_score / 10.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "relevance": round(self.relevance, 1),
            "completeness": round(self.completeness, 1),
            "coherence": round(self.coherence, 1),
            "hallucination_score": round(self.hallucination_score, 1),
            "overall_score": round(self.overall_score, 1),
            "normalized_overall": round(self.normalized_overall, 3),
        }
