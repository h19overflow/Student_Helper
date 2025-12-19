"""
Core metrics data classes for RAG evaluation.

Contains pure data containers for:
- RetrievalMetrics: NDCG, precision, recall, MRR
- CitationMetrics: Citation accuracy, precision, recall
- AnswerMetrics: Relevance, completeness, coherence
- PerformanceMetrics: Latency, tokens, cost
"""

from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    """Retrieval quality metrics.
    
    Measures how well the retrieval system finds relevant chunks.
    All scores are normalized to 0-1 range.
    """

    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mean_reciprocal_rank: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ndcg_at_5": round(self.ndcg_at_5, 3),
            "ndcg_at_10": round(self.ndcg_at_10, 3),
            "precision_at_5": round(self.precision_at_5, 3),
            "precision_at_10": round(self.precision_at_10, 3),
            "recall_at_5": round(self.recall_at_5, 3),
            "recall_at_10": round(self.recall_at_10, 3),
            "mean_reciprocal_rank": round(self.mean_reciprocal_rank, 3),
        }


@dataclass
class CitationMetrics:
    """Citation quality metrics.
    
    Measures how accurately the answer cites source documents.
    All scores are normalized to 0-1 range.
    """

    citation_accuracy: float = 0.0  # % of citations that match expected chunks
    citation_precision: float = 0.0  # % of retrieved docs that match expected
    citation_recall: float = 0.0  # % of expected chunks that were cited
    hallucination_rate: float = 0.0  # % of answer not supported by context

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "citation_accuracy": round(self.citation_accuracy, 3),
            "citation_precision": round(self.citation_precision, 3),
            "citation_recall": round(self.citation_recall, 3),
            "hallucination_rate": round(self.hallucination_rate, 3),
        }


@dataclass
class AnswerMetrics:
    """Answer quality metrics.
    
    Measures the quality of the generated answer.
    All scores are normalized to 0-1 range.
    """

    relevance_score: float = 0.0  # Semantic similarity to expected answer
    completeness: float = 0.0  # % of key points covered
    coherence: float = 0.0  # Linguistic coherence

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "relevance_score": round(self.relevance_score, 3),
            "completeness": round(self.completeness, 3),
            "coherence": round(self.coherence, 3),
        }


@dataclass
class PerformanceMetrics:
    """System performance metrics.
    
    Tracks latency, token usage, and costs for queries.
    """

    retrieval_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    embedding_tokens: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    total_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "retrieval_latency_ms": round(self.retrieval_latency_ms, 1),
            "llm_latency_ms": round(self.llm_latency_ms, 1),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "embedding_tokens": self.embedding_tokens,
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }
