"""
Evaluation models - Data classes and schemas for evaluation metrics.

This module contains all Pydantic/dataclass models used for:
- Retrieval quality metrics
- Citation quality metrics
- Answer quality metrics
- Performance metrics
- Evaluation results

All models are pure data containers with no business logic.
"""

from backend.evaluation.models.metrics_models import (
    RetrievalMetrics,
    CitationMetrics,
    AnswerMetrics,
    PerformanceMetrics,
)
from backend.evaluation.models.result_models import EvaluationResult
from backend.evaluation.models.ragas_models import RagasScores
from backend.evaluation.models.judge_models import JudgeScores

__all__ = [
    "RetrievalMetrics",
    "CitationMetrics",
    "AnswerMetrics",
    "PerformanceMetrics",
    "EvaluationResult",
    "RagasScores",
    "JudgeScores",
]
