"""
Helper utilities for the evaluation orchestrator.

Contains helper functions for:
- Computing retrieval metrics from chunks
- Computing citation metrics from chunks
- Extracting cited chunks from answer text

IMPORTANT: Development-only code. Not for production.
"""

import re
from typing import Optional

from backend.evaluation.models import (
    RetrievalMetrics,
    CitationMetrics,
)
from backend.evaluation.evaluators.metrics_calculator import MetricsCalculator
from backend.evaluation.evaluators.citation_calculator import CitationCalculator


def compute_retrieval_metrics(
    retrieved_chunks: list[str],
    expected_chunks: Optional[list[str]],
) -> RetrievalMetrics:
    """Compute retrieval quality metrics.
    
    Args:
        retrieved_chunks: IDs of chunks returned by retrieval
        expected_chunks: Expected chunk IDs from ground truth
        
    Returns:
        RetrievalMetrics with NDCG, precision, recall, MRR
    """
    if not expected_chunks:
        return RetrievalMetrics()

    return RetrievalMetrics(
        ndcg_at_5=MetricsCalculator.ndcg_at_k(
            retrieved_chunks, expected_chunks, k=5
        ),
        ndcg_at_10=MetricsCalculator.ndcg_at_k(
            retrieved_chunks, expected_chunks, k=10
        ),
        precision_at_5=MetricsCalculator.precision_at_k(
            retrieved_chunks, expected_chunks, k=5
        ),
        precision_at_10=MetricsCalculator.precision_at_k(
            retrieved_chunks, expected_chunks, k=10
        ),
        recall_at_5=MetricsCalculator.recall_at_k(
            retrieved_chunks, expected_chunks, k=5
        ),
        recall_at_10=MetricsCalculator.recall_at_k(
            retrieved_chunks, expected_chunks, k=10
        ),
        mean_reciprocal_rank=MetricsCalculator.mean_reciprocal_rank(
            retrieved_chunks, expected_chunks
        ),
    )


def compute_citation_metrics(
    cited_chunks: list[str],
    expected_chunks: Optional[list[str]],
) -> CitationMetrics:
    """Compute citation quality metrics.
    
    Args:
        cited_chunks: Chunk IDs cited in the answer
        expected_chunks: Expected chunk IDs from ground truth
        
    Returns:
        CitationMetrics with accuracy, precision, recall
    """
    if not expected_chunks:
        return CitationMetrics()

    return CitationMetrics(
        citation_accuracy=CitationCalculator.citation_accuracy(
            cited_chunks, expected_chunks
        ),
        citation_precision=CitationCalculator.citation_precision(
            cited_chunks, expected_chunks
        ),
        citation_recall=CitationCalculator.citation_recall(
            cited_chunks, expected_chunks
        ),
    )


def extract_cited_chunks(answer: str) -> list[str]:
    """Extract chunk IDs from answer text.
    
    Looks for patterns like [chunk_001], (chunk_002), etc.
    
    Args:
        answer: Generated answer text
        
    Returns:
        List of unique chunk IDs found in answer
    """
    pattern = r"chunk_\d{3,}"
    matches = re.findall(pattern, answer, re.IGNORECASE)
    return list(set(matches))  # Deduplicate
