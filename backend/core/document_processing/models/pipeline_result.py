"""
Pipeline result model for document processing.

Represents the outcome of processing a document through the pipeline.

Dependencies: pydantic
System role: Return type for DocumentPipeline.process()
"""

from pydantic import BaseModel, Field


class PipelineResult(BaseModel):
    """Result of document processing pipeline execution."""

    document_id: str = Field(description="Unique document identifier")
    chunk_count: int = Field(description="Number of chunks generated")
    output_path: str = Field(description="Path to saved JSON output")
    processing_time_ms: float = Field(description="Total processing time in milliseconds")
