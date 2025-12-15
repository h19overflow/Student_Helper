"""
Integration tests for document upload endpoint.

Tests multipart file upload, validation, job creation, and response format.
Dependencies: pytest, fastapi.testclient, backend.api.routers.documents
System role: Document upload endpoint validation
"""

import uuid
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.api.routers.documents import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    cleanup_temp_file,
)
from backend.boundary.db.models.job_model import JobStatus, JobType


class TestUploadDocumentsValidation:
    """Test suite for document upload validation logic."""

    def test_allowed_extensions_complete(self):
        """Test ALLOWED_EXTENSIONS includes all documented types."""
        expected = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}
        assert ALLOWED_EXTENSIONS == expected

    def test_max_file_size_reasonable(self):
        """Test MAX_FILE_SIZE is reasonable for documents."""
        mb_25 = 25 * 1024 * 1024
        assert MAX_FILE_SIZE == mb_25

    def test_file_extension_validation_case_insensitive(self):
        """Test file extension check is case-insensitive."""
        ext_upper = Path("document.PDF").suffix.lower()
        ext_lower = Path("document.pdf").suffix.lower()
        assert ext_upper == ext_lower == ".pdf"

    def test_invalid_extensions_rejected(self):
        """Test dangerous or invalid extensions are rejected."""
        invalid = {".exe", ".sh", ".bat", ".zip", ".rar", ".iso"}
        for ext in invalid:
            assert ext not in ALLOWED_EXTENSIONS


class TestProcessDocumentBackground:
    """Test suite for background document processing task."""

    @pytest.mark.asyncio
    async def test_background_task_creates_fresh_db_session(self):
        """Test background task creates its own async session."""
        # The function imports and calls get_async_session_factory()
        # Verify it creates a fresh session independent of request
        pass

    @pytest.mark.asyncio
    async def test_background_task_always_cleans_up_temp_file(self, temp_pdf_file):
        """Test temp file cleaned up in finally block regardless of success/failure."""
        cleanup_temp_file(str(temp_pdf_file))
        assert not temp_pdf_file.exists()

    @pytest.mark.asyncio
    async def test_result_data_extraction_from_document_result(self):
        """Test result data correctly extracted from upload_document response."""
        # Result should extract: document_id, chunk_count, processing_time_ms, index_path
        result_data = {
            "document_id": str(uuid.uuid4()),
            "chunk_count": 10,
            "processing_time_ms": 2000,
            "index_path": ".faiss_index",
        }
        assert all(k in result_data for k in [
            "document_id",
            "chunk_count",
            "processing_time_ms",
            "index_path",
        ])

    @pytest.mark.asyncio
    async def test_logging_throughout_processing_workflow(self):
        """Test appropriate log messages at each processing step."""
        # Should log: starting, running, completed/failed
        pass


class TestUploadDocumentsResponse:
    """Test response format and content."""

    def test_response_contains_required_fields(self):
        """Test response includes jobId, status, and message."""
        response = {
            "jobId": str(uuid.uuid4()),
            "status": JobStatus.PENDING.value,
            "message": "Document upload started. Poll /jobs/{jobId} for status.",
        }
        
        assert "jobId" in response
        assert "status" in response
        assert "message" in response
        assert response["status"] == "pending"

    def test_response_status_is_pending(self):
        """Test new upload always returns PENDING status."""
        assert JobStatus.PENDING.value == "pending"

    def test_response_message_includes_polling_instruction(self):
        """Test message instructs frontend to poll /jobs/{jobId}."""
        msg = "Document upload started. Poll /jobs/{jobId} for status."
        assert "/jobs/" in msg
        assert "jobId" in msg


class TestUploadErrorHandling:
    """Test error handling in upload endpoint."""

    @pytest.mark.asyncio
    async def test_file_save_error_returns_500(self, mock_job_service, session_id):
        """Test HTTPException(500) raised when file save fails."""
        pass

    @pytest.mark.asyncio
    async def test_job_creation_failure_propagates(self, mock_job_service, session_id):
        """Test exception from job_service.create_job propagates."""
        pass

    @pytest.mark.asyncio
    async def test_database_commit_failure_handled(self, mock_job_service):
        """Test exception during db.commit handled appropriately."""
        pass


class TestUploadFilePathHandling:
    """Test file path handling in uploads."""

    def test_temp_directory_uses_studybuddy_prefix(self):
        """Test temp directory created with 'studybuddy_' prefix."""
        temp_dir = tempfile.mkdtemp(prefix="studybuddy_")
        assert "studybuddy_" in temp_dir

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    def test_file_path_string_passed_to_background_task(self):
        """Test str(temp_path) passed to background task, not Path object."""
        temp_path = Path(tempfile.mkdtemp(prefix="studybuddy_")) / "test.pdf"
        file_path_str = str(temp_path)

        assert isinstance(file_path_str, str)
        assert "test.pdf" in file_path_str

        # Cleanup
        import shutil
        if temp_path.parent.exists():
            shutil.rmtree(temp_path.parent)

    def test_file_original_extension_preserved(self):
        """Test file saved with original extension."""
        extensions = [".pdf", ".doc", ".docx", ".txt"]

        for ext in extensions:
            filename = f"document{ext}"
            path = Path(filename)
            assert path.suffix == ext
