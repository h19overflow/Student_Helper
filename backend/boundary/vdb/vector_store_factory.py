"""
Vector store factory for selecting between FAISS (dev) and S3Vectors (prod).

Depends on VECTOR_STORE_TYPE environment variable.
Provides consistent interface regardless of underlying implementation.

Dependencies: backend.boundary.vdb, backend.configs
System role: Vector store instantiation and selection
"""

import logging

from backend.boundary.vdb.faiss_vectors_store import FAISSVectorsStore
from backend.boundary.vdb.s3_vectors_store import S3VectorsStore
from backend.configs import get_settings

logger = logging.getLogger(__name__)


def get_vector_store():
    """
    Factory function to get vector store based on environment configuration.

    Returns:
        FAISSVectorsStore or S3VectorsStore: Configured vector store instance

    Raises:
        ValueError: If VECTOR_STORE_TYPE is invalid
    """
    settings = get_settings()
    store_type = settings.vector_store.store_type.lower()

    if store_type == "faiss":
        logger.info(
            f"{__name__}:get_vector_store - Creating FAISS vector store (local dev mode)"
        )
        return FAISSVectorsStore(
            index_name=settings.vector_store.index_name,
            embedding_region=settings.vector_store.embedding_region,
            embedding_model_id=settings.vector_store.embedding_model,
        )

    elif store_type == "s3":
        logger.info(f"{__name__}:get_vector_store - Creating S3 Vectors store (production mode)")
        return S3VectorsStore(
            vectors_bucket=getattr(settings, "vectors_bucket", "student-helper-dev-vectors"),
            index_name=settings.vector_store.index_name,
            region=settings.vector_store.aws_region,
            embedding_region=settings.vector_store.embedding_region,
            embedding_model_id=settings.vector_store.embedding_model,
        )

    else:
        raise ValueError(
            f"Invalid VECTOR_STORE_TYPE: {store_type}. "
            f"Must be 'faiss' (dev) or 's3' (production)."
        )
