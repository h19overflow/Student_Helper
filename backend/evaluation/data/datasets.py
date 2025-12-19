"""
Ground truth dataset management for RAG evaluation.

Schema:
- question: User query
- expected_answer: Gold standard answer
- expected_chunks: Document chunk IDs that should be retrieved
- source_document: PDF filename for reference
- difficulty: easy|medium|hard
- category: topic classification

Usage:
    ds = GroundTruthDataset.from_json("ground_truth.json")
    for sample in ds.samples:
        print(sample.question, sample.expected_chunks)

IMPORTANT: Development-only code. Not for production.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GroundTruthSample:
    """Single ground truth evaluation sample.
    
    Represents a single Q&A pair with expected retrieval results
    for evaluation purposes.
    """

    question: str
    expected_answer: str
    expected_chunks: list[str]  # Chunk IDs that should be retrieved
    source_document: str  # PDF filename
    difficulty: str = "medium"  # easy|medium|hard
    category: str = "general"  # Topic classification
    min_citation_accuracy: float = 0.8  # Minimum acceptable accuracy
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "GroundTruthSample":
        """Create sample from dictionary."""
        return GroundTruthSample(**data)


@dataclass
class GroundTruthDataset:
    """Container for ground truth evaluation samples.
    
    Provides methods for loading, saving, and filtering samples.
    """

    samples: list[GroundTruthSample] = field(default_factory=list)

    def add_sample(self, sample: GroundTruthSample) -> None:
        """Add a sample to dataset."""
        self.samples.append(sample)

    def get_by_document(self, doc_name: str) -> list[GroundTruthSample]:
        """Get all samples from a specific document."""
        return [s for s in self.samples if s.source_document == doc_name]

    def get_by_difficulty(self, difficulty: str) -> list[GroundTruthSample]:
        """Filter by difficulty level."""
        return [s for s in self.samples if s.difficulty == difficulty]

    def get_by_category(self, category: str) -> list[GroundTruthSample]:
        """Filter by category."""
        return [s for s in self.samples if s.category == category]

    def save_json(self, path: Path | str) -> None:
        """Save dataset to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "total_samples": len(self.samples),
                "documents": len(set(s.source_document for s in self.samples)),
            },
            "samples": [s.to_dict() for s in self.samples],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self.samples)} samples to {path}")

    @staticmethod
    def from_json(path: Path | str) -> "GroundTruthDataset":
        """Load dataset from JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        dataset = GroundTruthDataset()
        for sample_data in data.get("samples", []):
            dataset.add_sample(GroundTruthSample.from_dict(sample_data))

        logger.info(f"Loaded {len(dataset.samples)} samples from {path}")
        return dataset

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)


# Template for creating ground truth JSON
GROUND_TRUTH_TEMPLATE = {
    "metadata": {
        "total_samples": 100,
        "documents": 5,
        "distribution": "20 per document",
    },
    "samples": [
        {
            "question": "What is the main topic of the document?",
            "expected_answer": "The document covers RAG systems and their implementation.",
            "expected_chunks": ["chunk_001", "chunk_002"],
            "source_document": "document_1.pdf",
            "difficulty": "easy",
            "category": "architecture",
            "min_citation_accuracy": 0.8,
            "metadata": {"tags": ["retrieval", "llm"]},
        }
    ],
}
