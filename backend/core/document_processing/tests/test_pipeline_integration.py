"""Unit tests for pipeline integration with handler."""

import pytest
import json
from uuid import uuid4
from unittest.mock import patch, MagicMock
from backend.core.document_processing.lambda_handler import handler
from backend.core.document_processing.models.pipeline_result import PipelineResult


@pytest.fixture(autouse=True)
def reset_pipeline_singleton():
    """Reset the pipeline singleton between tests."""
    if hasattr(handler, "_pipeline"):
        delattr(handler, "_pipeline")
    yield
    if hasattr(handler, "_pipeline"):
        delattr(handler, "_pipeline")


@pytest.fixture
def mock_db_updates():
    """Mock database status update functions."""
    with patch(
        "backend.core.document_processing.lambda_handler._update_status_processing"
    ) as mock_processing, patch(
        "backend.core.document_processing.lambda_handler._update_status_completed"
    ) as mock_completed, patch(
        "backend.core.document_processing.lambda_handler._update_status_failed"
    ) as mock_failed:
        # Make them async-compatible
        mock_processing.return_value = None
        mock_completed.return_value = None
        mock_failed.return_value = None
        yield {
            "processing": mock_processing,
            "completed": mock_completed,
            "failed": mock_failed,
        }


@patch.dict(
    "os.environ",
    {
        "DOCUMENTS_BUCKET": "test-bucket",
        "VECTORS_BUCKET": "vectors-bucket",
        "DATABASE_URL": "postgresql://test",
        "AWS_REGION": "us-east-1",
    },
)
@patch("backend.core.document_processing.lambda_handler.DocumentPipeline")
@patch("backend.core.document_processing.lambda_handler.asyncio.run")
def test_handler_processes_document(mock_asyncio_run, mock_pipeline_class):
    """Test handler calls pipeline with correct parameters."""
    # Mock asyncio.run to do nothing (skip DB updates)
    mock_asyncio_run.return_value = None

    # Setup mock pipeline
    mock_pipeline = MagicMock()
    mock_pipeline_class.return_value = mock_pipeline

    # Mock pipeline result
    mock_result = PipelineResult(
        document_id="550e8400-e29b-41d4-a716-446655440000",
        chunk_count=42,
        output_path="s3vectors://bucket/index/doc_id",
        processing_time_ms=2345,
    )
    mock_pipeline.process.return_value = mock_result

    # Create SQS event
    doc_id = uuid4()
    session_id = uuid4()
    event = {
        "Records": [
            {
                "messageId": "msg-123",
                "body": json.dumps(
                    {
                        "document_id": str(doc_id),
                        "session_id": str(session_id),
                        "s3_key": "documents/session_id/file.pdf",
                        "filename": "file.pdf",
                        "file_size_bytes": 1024,
                    }
                ),
            }
        ]
    }

    # Execute
    result = handler(event, None)

    # Verify
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["processed"] == 1
    assert body["failed"] == 0
    assert body["results"][0]["status"] == "success"
    assert body["results"][0]["chunk_count"] == 42
    assert body["results"][0]["processing_time_ms"] == 2345

    # Verify pipeline was called correctly
    mock_pipeline.process.assert_called_once_with(
        s3_key="documents/session_id/file.pdf",
        document_id=str(doc_id),
        session_id=str(session_id),
    )

    # Verify DB status updates were called (2 calls: processing + completed)
    assert mock_asyncio_run.call_count == 2


@patch.dict(
    "os.environ",
    {
        "DOCUMENTS_BUCKET": "test-bucket",
        "VECTORS_BUCKET": "vectors-bucket",
        "DATABASE_URL": "postgresql://test",
        "AWS_REGION": "us-east-1",
    },
)
@patch("backend.core.document_processing.lambda_handler.DocumentPipeline")
@patch("backend.core.document_processing.lambda_handler.asyncio.run")
def test_handler_pipeline_error(mock_asyncio_run, mock_pipeline_class):
    """Test handler catches pipeline errors."""
    # Mock asyncio.run to do nothing (skip DB updates)
    mock_asyncio_run.return_value = None

    # Setup mock pipeline to raise error
    mock_pipeline = MagicMock()
    mock_pipeline_class.return_value = mock_pipeline
    mock_pipeline.process.side_effect = Exception("S3 download failed")

    # Create SQS event
    doc_id = uuid4()
    session_id = uuid4()
    event = {
        "Records": [
            {
                "messageId": "msg-123",
                "body": json.dumps(
                    {
                        "document_id": str(doc_id),
                        "session_id": str(session_id),
                        "s3_key": "documents/session_id/file.pdf",
                        "filename": "file.pdf",
                        "file_size_bytes": 1024,
                    }
                ),
            }
        ]
    }

    # Execute
    result = handler(event, None)

    # Verify partial failure
    assert result["statusCode"] == 206  # Partial success
    body = json.loads(result["body"])
    assert body["failed"] == 1
    assert body["results"][0]["status"] == "failed"
    assert "S3 download failed" in body["results"][0]["details"]


@patch.dict(
    "os.environ",
    {
        "DOCUMENTS_BUCKET": "test-bucket",
        "VECTORS_BUCKET": "vectors-bucket",
        "DATABASE_URL": "postgresql://test",
        "AWS_REGION": "us-east-1",
    },
)
@patch("backend.core.document_processing.lambda_handler.DocumentPipeline")
@patch("backend.core.document_processing.lambda_handler.asyncio.run")
def test_handler_batch_processing(mock_asyncio_run, mock_pipeline_class):
    """Test handler processes multiple documents in batch."""
    # Mock asyncio.run to do nothing (skip DB updates)
    mock_asyncio_run.return_value = None

    mock_pipeline = MagicMock()
    mock_pipeline_class.return_value = mock_pipeline

    # Mock different results for each call
    mock_pipeline.process.side_effect = [
        PipelineResult(
            document_id="doc-1",
            chunk_count=42,
            output_path="s3vectors://bucket/index/doc-1",
            processing_time_ms=2345,
        ),
        PipelineResult(
            document_id="doc-2",
            chunk_count=28,
            output_path="s3vectors://bucket/index/doc-2",
            processing_time_ms=1567,
        ),
    ]

    # Create batch SQS event
    doc_id_1 = uuid4()
    session_id = uuid4()
    doc_id_2 = uuid4()

    event = {
        "Records": [
            {
                "messageId": "msg-1",
                "body": json.dumps(
                    {
                        "document_id": str(doc_id_1),
                        "session_id": str(session_id),
                        "s3_key": "documents/session_id/file1.pdf",
                        "filename": "file1.pdf",
                        "file_size_bytes": 1024,
                    }
                ),
            },
            {
                "messageId": "msg-2",
                "body": json.dumps(
                    {
                        "document_id": str(doc_id_2),
                        "session_id": str(session_id),
                        "s3_key": "documents/session_id/file2.pdf",
                        "filename": "file2.pdf",
                        "file_size_bytes": 2048,
                    }
                ),
            },
        ]
    }

    # Execute
    result = handler(event, None)

    # Verify
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["processed"] == 2
    assert body["failed"] == 0
    assert len(body["results"]) == 2
    assert body["results"][0]["chunk_count"] == 42
    assert body["results"][1]["chunk_count"] == 28

    # Verify pipeline called twice
    assert mock_pipeline.process.call_count == 2

    # Verify DB updates called (2 docs * 2 updates each = 4 calls)
    assert mock_asyncio_run.call_count == 4
