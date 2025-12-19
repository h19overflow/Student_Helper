"""
RAGAS (RAG Assessment) evaluation pipeline.

RAGAS provides automated metrics:
- Faithfulness: Answer is grounded in retrieved context
- Answer Relevance: Answer addresses the question
- Context Recall: Retrieved context contains answer-supporting info
- Context Precision: Retrieved context is relevant

Requires: pip install ragas

IMPORTANT: Development-only code. Not for production.
"""

import logging

from backend.evaluation.models.ragas_models import RagasScores

logger = logging.getLogger(__name__)

# Try to import RAGAS - graceful fallback if not installed
try:
    from ragas.metrics import (
        faithfulness,
        answer_relevance,
        context_recall,
        context_precision,
    )
    from ragas.llm import LangchainLLMWrapper
    from langchain_google_genai import ChatGoogleGenerativeAI

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("RAGAS not installed. Run: pip install ragas")


class RagasEvaluator:
    """RAGAS evaluation pipeline wrapper.
    
    Usage:
        evaluator = RagasEvaluator()
        scores = await evaluator.evaluate(
            question="What is RAG?",
            answer="RAG is Retrieval-Augmented Generation...",
            context="[Retrieved document chunks]",
        )
    """

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        """Initialize RAGAS evaluator.
        
        Args:
            model_name: LLM model to use for evaluation
            
        Raises:
            ImportError: If RAGAS is not installed
        """
        if not RAGAS_AVAILABLE:
            raise ImportError("RAGAS not installed. Run: pip install ragas")

        self.model = ChatGoogleGenerativeAI(model=model_name, temperature=0)
        self.evaluator_llm = LangchainLLMWrapper(self.model)
        logger.info(f"Initialized RAGAS evaluator with {model_name}")

    async def evaluate(
        self,
        question: str,
        answer: str,
        context: str,
    ) -> RagasScores:
        """Evaluate a single Q&A pair using RAGAS metrics.
        
        Args:
            question: User query
            answer: Generated answer
            context: Retrieved context (concatenated chunks)
            
        Returns:
            RagasScores object with all metrics
        """
        try:
            eval_data = {
                "question": question,
                "answer": answer,
                "contexts": [context],
            }

            faith_score = await self._compute_metric(faithfulness, eval_data)
            relevance_score = await self._compute_metric(
                answer_relevance, eval_data
            )
            recall_score = await self._compute_metric(context_recall, eval_data)
            precision_score = await self._compute_metric(
                context_precision, eval_data
            )

            scores = RagasScores(
                faithfulness=faith_score,
                answer_relevance=relevance_score,
                context_recall=recall_score,
                context_precision=precision_score,
            )

            logger.info(f"RAGAS evaluation complete: {scores.to_dict()}")
            return scores

        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {type(e).__name__}: {e}")
            return RagasScores()

    async def _compute_metric(self, metric_fn, eval_data: dict) -> float:
        """Safely compute a single RAGAS metric."""
        try:
            result = await metric_fn.ascore(**eval_data)
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.warning(f"Metric computation failed: {e}")
            return 0.0


class DummyRagasEvaluator:
    """Placeholder evaluator when RAGAS is not installed.
    
    Returns default scores so evaluation can continue without hard dependency.
    """

    async def evaluate(
        self,
        question: str,
        answer: str,
        context: str,
    ) -> RagasScores:
        """Return zero scores."""
        logger.warning(
            "Using dummy RAGAS evaluator. Install RAGAS: pip install ragas"
        )
        return RagasScores()


def create_ragas_evaluator(
    model_name: str = "gemini-3-flash-preview",
) -> RagasEvaluator | DummyRagasEvaluator:
    """Factory function to create appropriate RAGAS evaluator.
    
    Returns RagasEvaluator if available, DummyRagasEvaluator otherwise.
    """
    if RAGAS_AVAILABLE:
        return RagasEvaluator(model_name)
    else:
        logger.warning("RAGAS not available, using dummy evaluator")
        return DummyRagasEvaluator()
