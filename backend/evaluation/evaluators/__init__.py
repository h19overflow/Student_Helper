"""
Evaluation logic - Calculators and evaluators for RAG quality assessment.

This module contains all business logic for:
- Metrics calculation (NDCG, precision, recall, MRR)
- Citation accuracy calculation
- RAGAS integration
- LLM-as-Judge evaluation
- Main evaluation orchestrator
- Helper functions for metric computation

All data classes are imported from the models module.
"""

from backend.evaluation.evaluators.metrics_calculator import MetricsCalculator
from backend.evaluation.evaluators.citation_calculator import CitationCalculator
from backend.evaluation.evaluators.ragas_evaluator import (
    RagasEvaluator,
    DummyRagasEvaluator,
    create_ragas_evaluator,
    RAGAS_AVAILABLE,
)
from backend.evaluation.evaluators.llm_judge import LLMJudge
from backend.evaluation.evaluators.orchestrator import Evaluator
from backend.evaluation.evaluators.helpers import (
    compute_retrieval_metrics,
    compute_citation_metrics,
    extract_cited_chunks,
)

__all__ = [
    "MetricsCalculator",
    "CitationCalculator",
    "RagasEvaluator",
    "DummyRagasEvaluator",
    "create_ragas_evaluator",
    "RAGAS_AVAILABLE",
    "LLMJudge",
    "Evaluator",
    "compute_retrieval_metrics",
    "compute_citation_metrics",
    "extract_cited_chunks",
]
