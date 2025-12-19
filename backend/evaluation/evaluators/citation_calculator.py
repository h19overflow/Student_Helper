"""
Citation metrics calculator.

Contains algorithms for calculating citation quality metrics:
- Citation Accuracy
- Citation Precision
- Citation Recall

IMPORTANT: Development-only code. Not for production.
"""

import logging

logger = logging.getLogger(__name__)


class CitationCalculator:
    """Calculate citation evaluation metrics.
    
    All methods are static and can be called without instantiation.
    """

    @staticmethod
    def citation_accuracy(
        cited_chunks: list[str],
        expected_chunks: list[str],
    ) -> float:
        """Citation Accuracy.
        
        Percentage of cited chunks that match expected chunks.
        
        Args:
            cited_chunks: Chunks cited in the answer
            expected_chunks: Expected chunks from ground truth
            
        Returns:
            Accuracy score (0-1)
        """
        if not cited_chunks:
            return 0.0 if expected_chunks else 1.0

        correct = len(set(cited_chunks) & set(expected_chunks))
        return correct / len(cited_chunks)

    @staticmethod
    def citation_precision(
        cited_chunks: list[str],
        expected_chunks: list[str],
    ) -> float:
        """Citation Precision.
        
        Same as citation accuracy - percentage of cited chunks that are correct.
        
        Args:
            cited_chunks: Chunks cited in the answer
            expected_chunks: Expected chunks from ground truth
            
        Returns:
            Precision score (0-1)
        """
        return CitationCalculator.citation_accuracy(cited_chunks, expected_chunks)

    @staticmethod
    def citation_recall(
        cited_chunks: list[str],
        expected_chunks: list[str],
    ) -> float:
        """Citation Recall.
        
        Percentage of expected chunks that were cited.
        
        Args:
            cited_chunks: Chunks cited in the answer
            expected_chunks: Expected chunks from ground truth
            
        Returns:
            Recall score (0-1)
        """
        if not expected_chunks:
            return 1.0 if not cited_chunks else 0.0

        correct = len(set(cited_chunks) & set(expected_chunks))
        return correct / len(expected_chunks)
