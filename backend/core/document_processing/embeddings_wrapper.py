"""
Google Generative AI Embeddings wrapper with fixed output dimensionality.

Wraps GoogleGenerativeAIEmbeddings to ensure consistent vector dimensions
across all embedding calls. This is required because the base class ignores
output_dimensionality in the constructor.

Dependencies: langchain_google_genai
System role: Embedding dimension consistency for S3 Vectors compatibility
"""

import logging
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

class FixedDimensionEmbeddings(GoogleGenerativeAIEmbeddings):
    """
    GoogleGenerativeAIEmbeddings wrapper with fixed output dimensionality.

    The base GoogleGenerativeAIEmbeddings class ignores output_dimensionality
    in the constructor. This wrapper ensures all embed calls use the specified
    dimension, which is critical for S3 Vectors index compatibility.
    """

    _output_dimensionality: int = 1024

    def __init__(
        self,
        model: str = "models/gemini-embedding-001",
        output_dimensionality: int = 1024,
        **kwargs,
    ) -> None:
        """
        Initialize embeddings with fixed output dimensionality.

        Args:
            model: Google embedding model ID (default: gemini-embedding-001 for 1024-dim support)
            output_dimensionality: Fixed dimension for all embeddings (default: 1024)
            **kwargs: Additional arguments for GoogleGenerativeAIEmbeddings

        Note:
            text-embedding-004 only supports max 768 dimensions.
            gemini-embedding-001 supports up to 3072 dimensions, reducible to 1024.
        """
        super().__init__(model=model, **kwargs)
        self._output_dimensionality = output_dimensionality
        logger.info(
            f"{__name__}:__init__ - Initialized with model={model}, "
            f"output_dimensionality={output_dimensionality}"
        )

    def embed_documents(
        self,
        texts: List[str],
        *,
        batch_size: int = 100,
        task_type: str | None = None,
        titles: List[str] | None = None,
        output_dimensionality: int | None = None,
    ) -> List[List[float]]:
        """
        Embed documents with fixed output dimensionality.

        Overrides parent to always use the configured dimension unless
        explicitly overridden by the caller.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for API calls
            task_type: Optional task type for embedding
            titles: Optional titles for documents
            output_dimensionality: Override dimension (uses configured if None)

        Returns:
            List of embedding vectors
        """
        dim = output_dimensionality or self._output_dimensionality
        return super().embed_documents(
            texts,
            batch_size=batch_size,
            task_type=task_type,
            titles=titles,
            output_dimensionality=dim,
        )

    def embed_query(
        self,
        text: str,
        task_type: str | None = None,
        title: str | None = None,
        output_dimensionality: int | None = None,
    ) -> List[float]:
        """
        Embed query with fixed output dimensionality.

        Overrides parent to always use the configured dimension unless
        explicitly overridden by the caller.

        Args:
            text: Query text to embed
            task_type: Optional task type for embedding
            title: Optional title
            output_dimensionality: Override dimension (uses configured if None)

        Returns:
            Embedding vector
        """
        dim = output_dimensionality or self._output_dimensionality
        return super().embed_query(
            text,
            task_type=task_type,
            title=title,
            output_dimensionality=dim,
        )
