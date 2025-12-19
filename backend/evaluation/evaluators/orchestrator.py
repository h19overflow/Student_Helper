"""
Main evaluation orchestrator combining all evaluation methods.

IMPORTANT: Development-only code. Not for production.
"""

import logging
import time
from typing import Optional

from backend.evaluation.models import (
    AnswerMetrics,
    PerformanceMetrics,
    EvaluationResult,
)
from backend.evaluation.evaluators.ragas_evaluator import create_ragas_evaluator
from backend.evaluation.evaluators.llm_judge import LLMJudge
from backend.evaluation.evaluators.helpers import (
    compute_retrieval_metrics,
    compute_citation_metrics,
    extract_cited_chunks,
)

logger = logging.getLogger(__name__)


class Evaluator:
    """Complete evaluation orchestrator combining RAGAS and LLM-as-Judge."""

    def __init__(self, use_ragas: bool = True, use_llm_judge: bool = True):
        """Initialize with optional RAGAS and LLM judge evaluation."""
        self.use_ragas = use_ragas
        self.use_llm_judge = use_llm_judge

        if self.use_ragas:
            self.ragas_evaluator = create_ragas_evaluator()
        if self.use_llm_judge:
            self.llm_judge = LLMJudge()

        logger.info(f"Evaluator initialized (RAGAS={use_ragas}, LLMJudge={use_llm_judge})")

    async def evaluate(
        self,
        question: str,
        answer: str,
        retrieved_chunks: list[str],
        context: str,
        expected_answer: Optional[str] = None,
        expected_chunks: Optional[list[str]] = None,
        retrieval_latency_ms: float = 0.0,
        llm_latency_ms: float = 0.0,
        embedding_tokens: int = 0,
        llm_input_tokens: int = 0,
        llm_output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> EvaluationResult:
        """Comprehensive evaluation of a single Q&A pair."""
        start_time = time.time()

        retrieval_metrics = compute_retrieval_metrics(retrieved_chunks, expected_chunks)
        cited_chunks = extract_cited_chunks(answer)
        citation_metrics = compute_citation_metrics(cited_chunks, expected_chunks)
        answer_metrics = await self._compute_answer_metrics(
            question, answer, expected_answer, context
        )

        performance_metrics = PerformanceMetrics(
            retrieval_latency_ms=retrieval_latency_ms,
            llm_latency_ms=llm_latency_ms,
            total_latency_ms=retrieval_latency_ms + llm_latency_ms,
            embedding_tokens=embedding_tokens,
            llm_input_tokens=llm_input_tokens,
            llm_output_tokens=llm_output_tokens,
            total_cost_usd=cost_usd,
        )

        result = EvaluationResult(
            question=question,
            answer=answer,
            retrieval_metrics=retrieval_metrics,
            citation_metrics=citation_metrics,
            answer_metrics=answer_metrics,
            performance_metrics=performance_metrics,
        )

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Evaluation complete in {elapsed_ms:.1f}ms, score: {result.overall_score}")
        return result

    async def _compute_answer_metrics(
        self,
        question: str,
        answer: str,
        expected_answer: Optional[str],
        context: str,
    ) -> AnswerMetrics:
        """Compute answer quality metrics using RAGAS and LLM judge."""
        answer_metrics = AnswerMetrics()

        if self.use_ragas:
            answer_metrics = await self._run_ragas(question, answer, context, answer_metrics)

        if self.use_llm_judge and expected_answer:
            answer_metrics = await self._run_judge(
                question, answer, expected_answer, context, answer_metrics
            )

        return answer_metrics

    async def _run_ragas(
        self, question: str, answer: str, context: str, metrics: AnswerMetrics
    ) -> AnswerMetrics:
        """Run RAGAS evaluation and update metrics."""
        try:
            scores = await self.ragas_evaluator.evaluate(
                question=question, answer=answer, context=context
            )
            metrics.relevance_score = scores.answer_relevance
            metrics.coherence = scores.faithfulness
        except Exception as e:
            logger.warning(f"RAGAS evaluation failed: {e}")
        return metrics

    async def _run_judge(
        self,
        question: str,
        answer: str,
        expected_answer: str,
        context: str,
        metrics: AnswerMetrics,
    ) -> AnswerMetrics:
        """Run LLM judge evaluation and update metrics."""
        try:
            scores = await self.llm_judge.evaluate(
                question=question,
                answer=answer,
                expected_answer=expected_answer,
                context=context,
            )
            metrics.relevance_score = scores.relevance / 10.0
            metrics.completeness = scores.completeness / 10.0
            metrics.coherence = scores.coherence / 10.0
        except Exception as e:
            logger.warning(f"LLM judge evaluation failed: {e}")
        return metrics
