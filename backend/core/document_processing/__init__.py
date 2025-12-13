"""
Document processing pipeline for ingestion.

Self-contained Lambda-ready module for parsing, chunking, embedding, and saving documents.

Dependencies: langchain_docling, langchain, langchain_google_genai, pydantic
System role: Document ingestion pipeline entrypoint
"""

from .configs import (
    DocumentPipelineSettings,
    get_pipeline_settings,
)
from .entrypoint import DocumentPipeline
from .models import Chunk, PipelineResult

__all__ = [
    "DocumentPipeline",
    "DocumentPipelineSettings",
    "get_pipeline_settings",
    "Chunk",
    "PipelineResult",
]
