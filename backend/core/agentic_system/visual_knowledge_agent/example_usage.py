"""Example usage of visual knowledge agent with actual agent orchestration.

Demonstrates how to use the VisualKnowledgeAgent to generate interactive
concept diagrams from AI answers.

The agent handles:
1. Document expansion via RAG (with real vector store)
2. Concept curation via LLM (real Google Generative AI)
3. Diagram generation (real Gemini image API)
4. Image persistence to disk

Requires:
- GOOGLE_API_KEY environment variable set
- Vector store instance with similarity_search method

Run with: python -m backend.core.agentic_system.visual_knowledge_agent.example_usage
"""

import asyncio
import base64
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

from backend.boundary.vdb.vector_schemas import VectorMetadata, VectorSearchResult
from backend.core.agentic_system.visual_knowledge_agent.visual_knowledge_agent import (
    VisualKnowledgeAgent,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger(__name__)


def create_mock_vector_store():
    """Create mock vector store for demonstration.

    Returns:
        MagicMock: Mock vector store with similarity_search method
    """
    mock_docs = [
        VectorSearchResult(
            chunk_id="chunk_1",
            content="Machine Learning is a subset of AI that enables systems to learn from data. "
                   "It uses algorithms to identify patterns and make predictions without explicit programming.",
            metadata=VectorMetadata(
                session_id="example-session",
                doc_id="doc_1",
                chunk_id="chunk_1",
                page=1,
                source_uri="https://example.com/ml-intro",
            ),
            similarity_score=0.95,
        ),
        VectorSearchResult(
            chunk_id="chunk_2",
            content="Supervised learning requires labeled training data. "
                   "The algorithm learns the relationship between input features and target output.",
            metadata=VectorMetadata(
                session_id="example-session",
                doc_id="doc_2",
                chunk_id="chunk_2",
                page=1,
                source_uri="https://example.com/supervised-learning",
            ),
            similarity_score=0.92,
        ),
        VectorSearchResult(
            chunk_id="chunk_3",
            content="Neural networks are inspired by biological neural networks. "
                   "They consist of interconnected layers of artificial neurons.",
            metadata=VectorMetadata(
                session_id="example-session",
                doc_id="doc_3",
                chunk_id="chunk_3",
                page=1,
                source_uri="https://example.com/neural-networks",
            ),
            similarity_score=0.90,
        ),
        VectorSearchResult(
            chunk_id="chunk_4",
            content="Deep learning uses multiple layers of neural networks. "
                   "It's effective for computer vision, natural language processing, and more.",
            metadata=VectorMetadata(
                session_id="example-session",
                doc_id="doc_4",
                chunk_id="chunk_4",
                page=1,
                source_uri="https://example.com/deep-learning",
            ),
            similarity_score=0.88,
        ),
        VectorSearchResult(
            chunk_id="chunk_5",
            content="Backpropagation is the fundamental algorithm for training neural networks. "
                   "It computes gradients efficiently using the chain rule.",
            metadata=VectorMetadata(
                session_id="example-session",
                doc_id="doc_5",
                chunk_id="chunk_5",
                page=1,
                source_uri="https://example.com/backpropagation",
            ),
            similarity_score=0.85,
        ),
    ]

    mock_store = MagicMock()
    mock_store.similarity_search = MagicMock(return_value=mock_docs)
    return mock_store


def save_image(image_base64: str, mime_type: str, output_dir: str = "visual_knowledge_outputs") -> str:
    """Save base64-encoded image to disk.

    Args:
        image_base64: Base64-encoded image data
        mime_type: MIME type of image (e.g., "image/jpeg")
        output_dir: Directory to save images in

    Returns:
        str: Path to saved image file

    Raises:
        ValueError: If MIME type is unsupported
    """
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Determine file extension from MIME type
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        ext = mime_to_ext.get(mime_type)
        if not ext:
            raise ValueError(f"Unsupported MIME type: {mime_type}")

        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"visual_knowledge_{timestamp}{ext}"
        filepath = output_path / filename

        # Decode base64 and write to file
        image_data = base64.b64decode(image_base64)
        with open(filepath, "wb") as f:
            f.write(image_data)

        logger.info(f"{__name__}:save_image - Image saved to {filepath}")
        return str(filepath)

    except Exception as e:
        logger.error(
            f"{__name__}:save_image - {type(e).__name__}: {e}",
            exc_info=True
        )
        raise


async def run_example():
    """Run the complete visual knowledge pipeline using VisualKnowledgeAgent.

    Demonstrates:
    1. Creating VisualKnowledgeAgent with dependencies
    2. Invoking the agent with an AI answer
    3. Displaying results
    4. Saving the generated image
    """
    logger.info("=" * 80)
    logger.info("VISUAL KNOWLEDGE AGENT - EXAMPLE USAGE")
    logger.info("=" * 80)

    # Create dependencies
    logger.info("\n[1/3] Creating Visual Knowledge Agent...")
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required. "
                "Set it with: export GOOGLE_API_KEY='your-key'"
            )

        mock_vector_store = create_mock_vector_store()
        agent = VisualKnowledgeAgent(
            google_api_key=google_api_key,
            vector_store=mock_vector_store,
        )
        logger.info("✓ Agent created successfully")
    except Exception as e:
        logger.error(f"✗ Agent initialization failed: {e}")
        return

    # Prepare input
    ai_answer = (
        "Machine learning is transforming how we build intelligent systems. "
        "It enables computers to learn patterns from data without explicit programming. "
        "Key approaches include supervised learning, neural networks, and deep learning."
    )

    logger.info("\n[2/3] Generating visual knowledge...")
    logger.info(f"AI Answer: {ai_answer[:80]}...")

    try:
        # Run agent
        response = await agent.ainvoke(
            ai_answer=ai_answer,
            session_id="example-session-001",
        )
        logger.info("✓ Pipeline executed successfully")

        # Display results
        logger.info("\n[3/3] Results:")
        logger.info("-" * 80)

        # Main concepts
        logger.info("\nMain Concepts:")
        for concept in response.main_concepts:
            logger.info(f"  • {concept}")

        # Branches
        logger.info("\nExplorable Branches:")
        for branch in response.branches:
            logger.info(f"  • {branch.label}: {branch.description}")

        # Image info and save
        logger.info(f"\nImage Generated:")
        logger.info(f"  • Size: {len(response.image_base64)} characters (base64)")
        logger.info(f"  • MIME type: {response.mime_type}")
        logger.info(f"  • First 50 chars: {response.image_base64[:50]}...")

        # Save image to disk
        try:
            image_path = save_image(response.image_base64, response.mime_type)
            logger.info(f"  • Saved to: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to save image: {e}")

        # Full prompt
        logger.info(f"\nImage Generation Prompt:")
        logger.info(f"  {response.image_generation_prompt[:150]}...")

        logger.info("\n" + "=" * 80)
        logger.info("EXAMPLE COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"✗ Pipeline execution failed: {type(e).__name__}: {e}", exc_info=True)
        return


if __name__ == "__main__":
    asyncio.run(run_example())
