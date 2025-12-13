"""
Document pipeline orchestrator.

Coordinates parsing, chunking, embedding, and saving tasks.

Dependencies: All task modules, configs
System role: Pipeline orchestration (coordinates only)
"""

import time
import uuid

from .configs import (
    DocumentPipelineSettings,
    get_pipeline_settings,
)
from .models import PipelineResult
from .tasks import (
    ChunkingTask,
    EmbeddingTask,
    ParsingTask,
    SavingTask,
)


class DocumentPipeline:
    """Orchestrate document ingestion: parse -> chunk -> embed -> save."""

    def __init__(self, settings: DocumentPipelineSettings | None = None) -> None:
        """
        Initialize pipeline with configuration.

        Args:
            settings: Pipeline settings (uses defaults if None)
        """
        self._settings = settings or get_pipeline_settings()

        self._parsing_task = ParsingTask()
        self._chunking_task = ChunkingTask(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        self._embedding_task = EmbeddingTask(
            api_key=self._settings.google_api_key,
            model=self._settings.embedding_model,
        )
        self._saving_task = SavingTask(
            output_directory=self._settings.output_directory,
        )

    def process(
        self,
        file_path: str,
        document_id: str | None = None,
    ) -> PipelineResult:
        """
        Process document through full pipeline.

        Args:
            file_path: Path to document file
            document_id: Optional document ID (generated if None)

        Returns:
            PipelineResult: Processing result with chunk count and output path

        Raises:
            ParsingError: Document parsing failed
            ValueError: Chunking failed
            EmbeddingError: Embedding generation failed
        """
        start_time = time.perf_counter()
        doc_id = document_id or str(uuid.uuid4())

        # Parse document
        documents = self._parsing_task.parse(file_path)

        # Chunk documents
        chunked_documents = self._chunking_task.chunk(documents)

        # Generate embeddings
        chunks = self._embedding_task.embed(chunked_documents)

        # Save to local JSON
        output_path = self._saving_task.save(chunks, doc_id)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return PipelineResult(
            document_id=doc_id,
            chunk_count=len(chunks),
            output_path=output_path,
            processing_time_ms=elapsed_ms,
        )

    def process_batch(self, file_paths: list[str]) -> list[PipelineResult]:
        """
        Process multiple documents.

        Args:
            file_paths: List of document paths

        Returns:
            list[PipelineResult]: Results for each document
        """
        return [self.process(path) for path in file_paths]
