"""
Document processing pipeline for ingestion.

Self-contained Lambda-ready module for parsing, chunking, embedding, and saving documents.

Dependencies: langchain_docling, langchain, langchain_google_genai, pydantic
System role: Document ingestion pipeline entrypoint
"""

from backend.core.document_processing.configs import (
    DocumentPipelineSettings,
    get_pipeline_settings,
)
from backend.core.document_processing.entrypoint import DocumentPipeline
from backend.core.document_processing.models import Chunk, PipelineResult

__all__ = [
    "DocumentPipeline",
    "DocumentPipelineSettings",
    "get_pipeline_settings",
    "Chunk",
    "PipelineResult",
]
