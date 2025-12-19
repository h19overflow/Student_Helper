"""
Evaluation result model.

Contains the complete evaluation result container that combines
all metric types into a single comprehensive result.
"""

from dataclasses import dataclass

from backend.evaluation.models.metrics_models import (
    RetrievalMetrics,
    CitationMetrics,
    AnswerMetrics,
    PerformanceMetrics,
)


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single query.
    
    Aggregates all metric types and provides an overall weighted score.
    """

    question: str
    answer: str
    retrieval_metrics: RetrievalMetrics
    citation_metrics: CitationMetrics
    answer_metrics: AnswerMetrics
    performance_metrics: PerformanceMetrics

    @property
    def overall_score(self) -> float:
        """Weighted overall score (0-100).
        
        Weights:
        - Retrieval (NDCG@5): 30%
        - Citation accuracy: 30%
        - Answer relevance: 20%
        - Latency performance: 20%
        """
        weights = {
            "retrieval": 0.3,
            "citation": 0.3,
            "answer": 0.2,
            "latency": 0.2,
        }

        retrieval_score = self.retrieval_metrics.ndcg_at_5 * 100
        citation_score = self.citation_metrics.citation_accuracy * 100
        answer_score = self.answer_metrics.relevance_score * 100

        # Latency: penalize if > 3s
        latency_score = self._calculate_latency_score()

        overall = (
            retrieval_score * weights["retrieval"]
            + citation_score * weights["citation"]
            + answer_score * weights["answer"]
            + latency_score * weights["latency"]
        )

        return round(overall, 2)

    def _calculate_latency_score(self) -> float:
        """Calculate latency score (0-100).
        
        - < 3000ms: 100 points
        - > 3000ms: linearly decreasing
        """
        if self.performance_metrics.total_latency_ms < 3000:
            return 100
        return max(
            0, 100 - (self.performance_metrics.total_latency_ms - 3000) / 10
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "question": self.question,
            "answer": self.answer,
            "retrieval": self.retrieval_metrics.to_dict(),
            "citation": self.citation_metrics.to_dict(),
            "answer_metrics": self.answer_metrics.to_dict(),
            "performance": self.performance_metrics.to_dict(),
            "overall_score": self.overall_score,
        }
