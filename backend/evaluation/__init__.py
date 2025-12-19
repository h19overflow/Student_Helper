"""
Evaluation module for RAG system performance measurement.

Contains:
- models/: Data classes and schemas for evaluation metrics
- evaluators/: Evaluation logic and calculators
- data/: Ground truth datasets and data loading

IMPORTANT: This module is for development/benchmarking only.
Production should not import or use evaluation code.

Usage:
    from backend.evaluation import Evaluator, GroundTruthDataset
    
    dataset = GroundTruthDataset.from_json("backend/evaluation/data/ground_truth.json")
    evaluator = Evaluator(use_ragas=True, use_llm_judge=True)
    
    result = await evaluator.evaluate(
        question="What is RAG?",
        answer="RAG is...",
        retrieved_chunks=["chunk_001"],
        context="...",
        expected_answer="...",
        expected_chunks=["chunk_001"],
    )
"""

# Models - Data classes
from backend.evaluation.models import (
    RetrievalMetrics,
    CitationMetrics,
    AnswerMetrics,
    PerformanceMetrics,
    EvaluationResult,
    RagasScores,
    JudgeScores,
)

# Evaluators - Business logic
from backend.evaluation.evaluators import (
    MetricsCalculator,
    CitationCalculator,
    RagasEvaluator,
    DummyRagasEvaluator,
    create_ragas_evaluator,
    RAGAS_AVAILABLE,
    LLMJudge,
    Evaluator,
)

# Data - Ground truth management
from backend.evaluation.data import (
    GroundTruthSample,
    GroundTruthDataset,
    GROUND_TRUTH_TEMPLATE,
)

__all__ = [
    # Models
    "RetrievalMetrics",
    "CitationMetrics",
    "AnswerMetrics",
    "PerformanceMetrics",
    "EvaluationResult",
    "RagasScores",
    "JudgeScores",
    # Evaluators
    "MetricsCalculator",
    "CitationCalculator",
    "RagasEvaluator",
    "DummyRagasEvaluator",
    "create_ragas_evaluator",
    "RAGAS_AVAILABLE",
    "LLMJudge",
    "Evaluator",
    # Data
    "GroundTruthSample",
    "GroundTruthDataset",
    "GROUND_TRUTH_TEMPLATE",
]
