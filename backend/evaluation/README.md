# RAG Evaluation Framework

**IMPORTANT:** This module is for **development and benchmarking only**. It is NOT imported or used in production.

## Overview

Complete evaluation framework for measuring RAG system quality with three complementary approaches:

1. **Manual Metrics** - Precision, recall, NDCG (standard IR metrics)
2. **RAGAS** - Automated evaluation (faithfulness, relevance, recall, precision)
3. **LLM-as-Judge** - Detailed quality assessment (relevance, completeness, coherence, hallucination)

## Module Structure

```
backend/evaluation/
├── __init__.py                    # Main exports
├── README.md                      # This file
│
├── models/                        # Data classes / schemas
│   ├── __init__.py                # Model exports
│   ├── metrics_models.py          # RetrievalMetrics, CitationMetrics, etc.
│   ├── result_models.py           # EvaluationResult
│   ├── ragas_models.py            # RagasScores
│   └── judge_models.py            # JudgeScores
│
├── evaluators/                    # Evaluation logic / calculators
│   ├── __init__.py                # Evaluator exports
│   ├── metrics_calculator.py      # NDCG, precision, recall, MRR
│   ├── citation_calculator.py     # Citation accuracy metrics
│   ├── ragas_evaluator.py         # RAGAS integration
│   ├── llm_judge.py               # LLM-as-Judge evaluation
│   └── orchestrator.py            # Main Evaluator class
│
└── data/                          # Data management
    ├── __init__.py                # Data exports
    ├── datasets.py                # GroundTruthSample, GroundTruthDataset
    └── ground_truth.json          # 100 Q&A samples (5 docs × 20)
```

## Quick Start

### 1. Load Ground Truth Dataset

```python
from backend.evaluation import GroundTruthDataset

# Load the 100 Q&A samples (20 per document)
dataset = GroundTruthDataset.from_json("backend/evaluation/data/ground_truth.json")

print(f"Loaded {len(dataset)} samples")
print(f"Documents: {len(set(s.source_document for s in dataset))}")

# Filter by difficulty
easy_samples = dataset.get_by_difficulty("easy")
hard_samples = dataset.get_by_difficulty("hard")

# Filter by document
doc_samples = dataset.get_by_document("document_1.pdf")
```

### 2. Evaluate a Single Query

```python
import asyncio
from backend.evaluation import Evaluator

evaluator = Evaluator(use_ragas=True, use_llm_judge=True)

result = await evaluator.evaluate(
    question="What is RAG?",
    answer="RAG is Retrieval-Augmented Generation...",
    retrieved_chunks=["chunk_001", "chunk_002"],
    context="[Retrieved context]",
    expected_answer="Expected answer from ground truth",
    expected_chunks=["chunk_001", "chunk_002"],
    retrieval_latency_ms=120,
    llm_latency_ms=450,
    embedding_tokens=150,
    llm_input_tokens=500,
    llm_output_tokens=120,
    cost_usd=0.0032,
)

print(f"Overall Score: {result.overall_score}/100")
print(f"Citation Accuracy: {result.citation_metrics.citation_accuracy:.1%}")
print(f"NDCG@5: {result.retrieval_metrics.ndcg_at_5:.3f}")
print(f"Answer Relevance: {result.answer_metrics.relevance_score:.3f}")
```

### 3. Use Individual Calculators

```python
from backend.evaluation import MetricsCalculator, CitationCalculator

# Calculate retrieval metrics
ndcg = MetricsCalculator.ndcg_at_k(
    retrieved_chunks=["chunk_001", "chunk_003", "chunk_002"],
    expected_chunks=["chunk_001", "chunk_002"],
    k=5,
)

# Calculate citation metrics
accuracy = CitationCalculator.citation_accuracy(
    cited_chunks=["chunk_001", "chunk_003"],
    expected_chunks=["chunk_001", "chunk_002"],
)
```

### 4. Benchmark Against Ground Truth

```python
import json
from backend.evaluation import Evaluator, GroundTruthDataset

# Load ground truth
dataset = GroundTruthDataset.from_json("backend/evaluation/data/ground_truth.json")
evaluator = Evaluator()

results = []
for sample in dataset[:10]:  # Test first 10
    # Call your RAG system...
    result = await evaluator.evaluate(
        question=sample.question,
        answer=answer,
        retrieved_chunks=retrieved,
        context=context,
        expected_answer=sample.expected_answer,
        expected_chunks=sample.expected_chunks,
    )
    results.append(result.to_dict())

# Save baseline
with open("baselines/baseline_v1.json", "w") as f:
    json.dump({
        "date": "2025-12-20",
        "samples_tested": len(results),
        "results": results,
        "average_score": sum(r["overall_score"] for r in results) / len(results),
    }, f, indent=2)
```

## Metrics Explained

### Retrieval Metrics (MetricsCalculator)

- **NDCG@5** (0-1): Normalized ranking quality
- **Precision@5** (0-1): % of top-5 retrieved that are relevant
- **Recall@5** (0-1): % of relevant chunks found in top-5
- **MRR** (0-1): Position of first relevant result (inverse)

### Citation Metrics (CitationCalculator)

- **Citation Accuracy** (0-1): % of cited chunks that match expected
- **Citation Precision** (0-1): Same as accuracy
- **Citation Recall** (0-1): % of expected chunks that were cited

### Answer Metrics (RAGAS + LLM Judge)

- **Relevance** (0-1): Does answer address the question?
- **Completeness** (0-1): Does answer cover key points?
- **Coherence** (0-1): Is answer clear and well-structured?

### Performance Metrics

- **Latency** (ms): Total query time
- **Cost** (USD): Total API costs for query

## Data Classes (models/)

All data classes are pure containers with no business logic:

```python
from backend.evaluation.models import (
    RetrievalMetrics,   # NDCG, precision, recall, MRR
    CitationMetrics,    # Citation accuracy, precision, recall
    AnswerMetrics,      # Relevance, completeness, coherence
    PerformanceMetrics, # Latency, tokens, cost
    EvaluationResult,   # Complete result with overall score
    RagasScores,        # RAGAS evaluation scores
    JudgeScores,        # LLM judge scores
)
```

## Requirements

```bash
# Required (no additional installs needed)
python >= 3.10
langchain-google-genai

# Optional (for RAGAS metrics)
pip install ragas

# For detailed evaluation
pip install pandas scikit-learn
```

## Best Practices

1. **Always evaluate against ground truth** before deploying changes
2. **Test at least 50 samples** per experiment for statistical significance
3. **Track both metrics and timing** - don't sacrifice quality for speed
4. **Document surprising results** - investigate why metrics improved/degraded
5. **Version your experiments** - save results with timestamp and configuration

## Production Notes

⚠️ **This module should NOT be imported in production code:**

```python
# ❌ NEVER in production
from backend.evaluation import Evaluator

# ✅ ONLY in development/testing
if ENVIRONMENT == "development":
    from backend.evaluation import Evaluator
```

The evaluation code adds latency and dependencies that should not be in critical paths.
