"""
LLM-as-Judge evaluation for detailed quality assessment.

Uses an LLM to evaluate answer quality on multiple dimensions:
- Relevance: Does answer address the question?
- Completeness: Does answer cover key points?
- Coherence: Is answer well-structured and clear?
- Hallucination: Does answer contain unsupported claims?

Requires: Google Generative AI credentials

IMPORTANT: Development-only code. Not for production.
"""

import logging
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from backend.evaluation.models.judge_models import JudgeScores

logger = logging.getLogger(__name__)


class LLMJudge:
    """LLM-as-Judge evaluator.
    
    Uses an LLM to provide detailed quality assessment.
    
    Usage:
        judge = LLMJudge()
        scores = await judge.evaluate(
            question="What is RAG?",
            answer="RAG is...",
            expected_answer="RAG is Retrieval-Augmented Generation...",
            context="[Retrieved documents]",
        )
    """

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        """Initialize LLM judge."""
        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
        )
        logger.info(f"Initialized LLM Judge with {model_name}")

    async def evaluate(
        self,
        question: str,
        answer: str,
        expected_answer: str,
        context: str,
    ) -> JudgeScores:
        """Evaluate answer quality using LLM.
        
        Args:
            question: Original user question
            answer: Generated answer
            expected_answer: Expected/reference answer
            context: Retrieved context
            
        Returns:
            JudgeScores with detailed assessment
        """
        try:
            prompt = self._build_evaluation_prompt(
                question=question,
                answer=answer,
                expected_answer=expected_answer,
                context=context,
            )

            message = HumanMessage(content=prompt)
            response = await self.model.ainvoke([message])
            scores = self._parse_response(response.content)

            logger.info(f"LLM Judge evaluation: {scores.to_dict()}")
            return scores

        except Exception as e:
            logger.error(
                f"LLM Judge evaluation failed: {type(e).__name__}: {e}"
            )
            return JudgeScores()

    def _build_evaluation_prompt(
        self,
        question: str,
        answer: str,
        expected_answer: str,
        context: str,
    ) -> str:
        """Build evaluation prompt for the LLM judge."""
        return f"""You are an expert evaluator assessing the quality of an AI-generated answer.

QUESTION:
{question}

EXPECTED/REFERENCE ANSWER:
{expected_answer}

RETRIEVED CONTEXT:
{context}

GENERATED ANSWER TO EVALUATE:
{answer}

---

Evaluate the generated answer on these criteria (0-10 scale):

1. RELEVANCE (0-10): Does the answer address the question directly?
   - 10: Perfectly addresses the question
   - 5: Partially addresses the question
   - 0: Irrelevant to the question

2. COMPLETENESS (0-10): Does the answer cover all key points from expected answer?
   - 10: Covers all key points
   - 5: Covers some key points
   - 0: Missing major points

3. COHERENCE (0-10): Is the answer well-structured and easy to understand?
   - 10: Clear, well-organized, professional
   - 5: Somewhat clear but could be better
   - 0: Confusing, poorly organized

4. HALLUCINATION (0-10): Does the answer contain unsupported or false claims?
   - 10: No hallucinations, fully grounded in context
   - 5: Minor hallucinations or unsupported claims
   - 0: Significant hallucinations or false information

---

Respond in JSON format ONLY (no markdown, no extra text):
{{
    "relevance": <0-10>,
    "completeness": <0-10>,
    "coherence": <0-10>,
    "hallucination_score": <0-10>,
    "overall_score": <0-10>,
    "reasoning": "<brief explanation>"
}}"""

    def _parse_response(self, response_text: str) -> JudgeScores:
        """Parse LLM response JSON.
        
        Handles various formats (markdown code blocks, etc).
        """
        try:
            text = response_text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())

            scores = JudgeScores(
                relevance=float(data.get("relevance", 0)),
                completeness=float(data.get("completeness", 0)),
                coherence=float(data.get("coherence", 0)),
                hallucination_score=float(data.get("hallucination_score", 0)),
                overall_score=float(data.get("overall_score", 0)),
            )

            # Clamp scores to 0-10 range
            scores.relevance = min(10, max(0, scores.relevance))
            scores.completeness = min(10, max(0, scores.completeness))
            scores.coherence = min(10, max(0, scores.coherence))
            scores.hallucination_score = min(
                10, max(0, scores.hallucination_score)
            )
            scores.overall_score = min(10, max(0, scores.overall_score))

            return scores

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse LLM judge response: {e}")
            logger.debug(f"Raw response: {response_text}")
            return JudgeScores()
