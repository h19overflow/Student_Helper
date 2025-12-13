"""
Local JSON persistence task for processed chunks.

Saves chunks with embeddings to JSON files for local development.

Dependencies: json, pathlib, datetime
System role: Final stage of document ingestion pipeline
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.core.document_processing.models import Chunk


class SavingTask:
    """Save processed chunks to local JSON files."""

    def __init__(self, output_directory: str) -> None:
        """
        Initialize saving task with output directory.

        Args:
            output_directory: Directory path for JSON output

        Creates directory if it does not exist.
        """
        self._output_dir = Path(output_directory)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, chunks: list[Chunk], document_id: str) -> str:
        """
        Save chunks to JSON file.

        Args:
            chunks: Processed chunks with embeddings
            document_id: Unique document identifier for filename

        Returns:
            str: Path to saved JSON file

        Raises:
            OSError: When file writing fails
        """
        output_path = self._output_dir / f"{document_id}.json"

        output_data = {
            "document_id": document_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": len(chunks),
            "chunks": [self._serialize_chunk(chunk) for chunk in chunks],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def _serialize_chunk(self, chunk: Chunk) -> dict:
        """
        Convert Chunk to JSON-serializable dict.

        Args:
            chunk: Chunk model instance

        Returns:
            dict: Serializable chunk data
        """
        return {
            "id": chunk.id,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding,
        }
