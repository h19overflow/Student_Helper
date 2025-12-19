"""
Retrieval metrics calculator.

Contains algorithms for calculating information retrieval metrics:
- NDCG (Normalized Discounted Cumulative Gain)
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)

IMPORTANT: Development-only code. Not for production.
"""

import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate retrieval evaluation metrics.
    
    All methods are static and can be called without instantiation.
    """

    @staticmethod
    def ndcg_at_k(
        retrieved_chunks: list[str],
        expected_chunks: list[str],
        k: int = 5,
    ) -> float:
        """Normalized Discounted Cumulative Gain @ K.
        
        Measures ranking quality of retrieved chunks.
        Higher = better (1.0 is perfect).
        
        Args:
            retrieved_chunks: Ranked list of retrieved chunk IDs
            expected_chunks: List of relevant chunk IDs
            k: Cutoff rank
            
        Returns:
            NDCG score (0-1)
        """
        if not expected_chunks:
            return 0.0

        dcg = 0.0
        for i, chunk_id in enumerate(retrieved_chunks[:k], 1):
            if chunk_id in expected_chunks:
                dcg += 1.0 / (i + 1)  # log2(i+1) simplified

        # Ideal DCG: all expected chunks ranked first
        idcg = sum(1.0 / (i + 1) for i in range(min(len(expected_chunks), k)))

        if idcg == 0:
            return 0.0

        return dcg / idcg

    @staticmethod
    def precision_at_k(
        retrieved_chunks: list[str],
        expected_chunks: list[str],
        k: int = 5,
    ) -> float:
        """Precision @ K.
        
        Percentage of top-k retrieved chunks that are relevant.
        
        Args:
            retrieved_chunks: Ranked list of retrieved chunk IDs
            expected_chunks: List of relevant chunk IDs
            k: Cutoff rank
            
        Returns:
            Precision score (0-1)
        """
        if not retrieved_chunks[:k]:
            return 0.0

        relevant_retrieved = len(
            set(retrieved_chunks[:k]) & set(expected_chunks)
        )
        return relevant_retrieved / min(k, len(retrieved_chunks))

    @staticmethod
    def recall_at_k(
        retrieved_chunks: list[str],
        expected_chunks: list[str],
        k: int = 5,
    ) -> float:
        """Recall @ K.
        
        Percentage of expected chunks that appear in top-k retrieved.
        
        Args:
            retrieved_chunks: Ranked list of retrieved chunk IDs
            expected_chunks: List of relevant chunk IDs
            k: Cutoff rank
            
        Returns:
            Recall score (0-1)
        """
        if not expected_chunks:
            return 0.0

        relevant_retrieved = len(
            set(retrieved_chunks[:k]) & set(expected_chunks)
        )
        return relevant_retrieved / len(expected_chunks)

    @staticmethod
    def mean_reciprocal_rank(
        retrieved_chunks: list[str],
        expected_chunks: list[str],
    ) -> float:
        """Mean Reciprocal Rank.
        
        Position of first relevant chunk (inverse).
        
        Args:
            retrieved_chunks: Ranked list of retrieved chunk IDs
            expected_chunks: List of relevant chunk IDs
            
        Returns:
            MRR score (0-1)
        """
        if not expected_chunks:
            return 0.0

        for i, chunk_id in enumerate(retrieved_chunks, 1):
            if chunk_id in expected_chunks:
                return 1.0 / i

        return 0.0  # No relevant chunks found
