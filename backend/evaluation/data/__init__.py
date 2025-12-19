"""
Data management - Ground truth datasets and data loading.

This module contains:
- GroundTruthSample: Single evaluation sample
- GroundTruthDataset: Container for evaluation samples
- Data loading and saving utilities
"""

from backend.evaluation.data.datasets import (
    GroundTruthSample,
    GroundTruthDataset,
    GROUND_TRUTH_TEMPLATE,
)

__all__ = [
    "GroundTruthSample",
    "GroundTruthDataset",
    "GROUND_TRUTH_TEMPLATE",
]
