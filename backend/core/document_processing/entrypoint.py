"""
Document pipeline orchestrator.

Coordinates S3 download, parsing, chunking, and S3 Vectors upload tasks.
VectorStoreTask handles embedding generation via Bedrock internally.

Dependencies: All task modules, configs
System role: Pipeline orchestration (coordinates only)
"""

import os
import shutil
import time
import uuid

from .configs import (
    DocumentPipelineSettings,
    get_pipeline_settings,
)
from .models import PipelineResult
from .tasks import (
    ChunkingTask,
    ParsingTask,
    S3DownloadTask,
    VectorStoreTask,
)


class DocumentPipeline:
    """Orchestrate document ingestion: S3 download -> parse -> chunk -> embed+upload."""

    def __init__(self, settings: DocumentPipelineSettings | None = None) -> None:
        """
        Initialize pipeline with configuration.

        Args:
            settings: Pipeline settings (uses defaults if None)
        """
        self._settings = settings or get_pipeline_settings()

        self._s3_download_task = S3DownloadTask(
            bucket=self._settings.documents_bucket,
            region=self._settings.bedrock_region,
        )
        self._parsing_task = ParsingTask()
        self._chunking_task = ChunkingTask(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        self._vector_store_task = VectorStoreTask(
            vectors_bucket=self._settings.vectors_bucket,
            index_name=self._settings.vectors_index,
            region=self._settings.bedrock_region,
            embedding_region=self._settings.embedding_region,
            embedding_model_id=self._settings.embedding_model_id,
        )

    def process(
        self,
        file_path: str | None = None,
        s3_key: str | None = None,
        document_id: str | None = None,
        session_id: str | None = None,
    ) -> PipelineResult:
        """
        Process document through full pipeline.

        Accepts either a local file_path OR an s3_key. If s3_key is provided,
        downloads from S3 first, then processes through the pipeline.

        Args:
            file_path: Path to local document file (mutually exclusive with s3_key)
            s3_key: S3 object key to download (mutually exclusive with file_path)
            document_id: Optional document ID (generated if None)
            session_id: Optional session ID (required for S3 Vectors)

        Returns:
            PipelineResult: Processing result with chunk count and output path

        Raises:
            ValueError: Neither file_path nor s3_key provided
            S3DownloadError: S3 download failed
            ParsingError: Document parsing failed
            VectorStoreUploadError: S3 Vectors upload failed
        """
        if not file_path and not s3_key:
            raise ValueError("Either file_path or s3_key must be provided")

        start_time = time.perf_counter()
        doc_id = document_id or str(uuid.uuid4())
        sess_id = session_id or str(uuid.uuid4())
        downloaded_from_s3 = False
        local_path = file_path

        try:
            # Download from S3 if s3_key provided
            if s3_key:
                local_path = self._s3_download_task.download(s3_key)
                downloaded_from_s3 = True

            # At this point local_path is guaranteed to be set
            assert local_path is not None, "local_path must be set"

            # Parse document
            documents = self._parsing_task.parse(local_path)

            # Chunk documents
            chunked_documents = self._chunking_task.chunk(documents)

            # Upload to S3 Vectors (embedding generated internally)
            chunk_ids = self._vector_store_task.upload(chunked_documents, doc_id, sess_id)
            output_path = f"s3vectors://{self._settings.vectors_bucket}/{self._settings.vectors_index}/{doc_id}"

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return PipelineResult(
                document_id=doc_id,
                chunk_count=len(chunk_ids),
                output_path=output_path,
                processing_time_ms=elapsed_ms,
            )

        finally:
            # Cleanup temp file if downloaded from S3
            if downloaded_from_s3 and local_path:
                temp_dir = os.path.dirname(local_path)
                shutil.rmtree(temp_dir, ignore_errors=True)

    def process_batch(self, file_paths: list[str]) -> list[PipelineResult]:
        """
        Process multiple documents.

        Args:
            file_paths: List of document paths

        Returns:
            list[PipelineResult]: Results for each document
        """
        return [self.process(path) for path in file_paths]


if __name__ == "__main__":
    pipeline = DocumentPipeline()
    result = pipeline.process("Hamza_CV.pdf")
    print(result)