"""Unit tests for document status updater."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from backend.core.document_processing.database.document_status_updater import (
    DocumentStatusUpdater,
    DocumentStatus,
)


@pytest.mark.asyncio
async def test_mark_processing():
    """Test marking document as PROCESSING."""
    mock_session = AsyncMock()
    doc_id = str(uuid4())

    # Mock execute result with a row (document found)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (doc_id,)  # RETURNING id
    mock_session.execute.return_value = mock_result

    updater = DocumentStatusUpdater(mock_session)
    await updater.mark_processing(doc_id)

    # Verify SQL was executed with correct status
    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args
    assert call_args[0][1]["status"] == DocumentStatus.PROCESSING.value
    assert call_args[0][1]["doc_id"] == doc_id
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mark_processing_not_found():
    """Test error when document not found."""
    mock_session = AsyncMock()

    # Mock execute result with no row (document not found)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_session.execute.return_value = mock_result

    updater = DocumentStatusUpdater(mock_session)

    with pytest.raises(ValueError, match="Document .* not found"):
        await updater.mark_processing(str(uuid4()))

    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_mark_completed():
    """Test marking document as COMPLETED."""
    mock_session = AsyncMock()
    doc_id = str(uuid4())

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (doc_id,)
    mock_session.execute.return_value = mock_result

    updater = DocumentStatusUpdater(mock_session)
    await updater.mark_completed(document_id=doc_id)

    # Verify SQL was executed with correct status
    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args
    assert call_args[0][1]["status"] == DocumentStatus.COMPLETED.value
    assert call_args[0][1]["doc_id"] == doc_id
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mark_failed():
    """Test marking document as FAILED."""
    mock_session = AsyncMock()
    doc_id = str(uuid4())

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (doc_id,)
    mock_session.execute.return_value = mock_result

    error_msg = "S3 download failed: bucket not found"
    updater = DocumentStatusUpdater(mock_session)
    await updater.mark_failed(document_id=doc_id, error_message=error_msg)

    # Verify SQL was executed with correct status and error message
    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args
    assert call_args[0][1]["status"] == DocumentStatus.FAILED.value
    assert call_args[0][1]["error_msg"] == error_msg
    assert call_args[0][1]["doc_id"] == doc_id
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mark_failed_rollback_on_error():
    """Test rollback on database error."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database error")

    updater = DocumentStatusUpdater(mock_session)

    with pytest.raises(Exception, match="Database error"):
        await updater.mark_failed(str(uuid4()), "error")

    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_mark_failed_truncates_long_error():
    """Test that long error messages are truncated."""
    mock_session = AsyncMock()
    doc_id = str(uuid4())

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (doc_id,)
    mock_session.execute.return_value = mock_result

    # Create error message longer than 2000 chars
    long_error = "x" * 3000
    updater = DocumentStatusUpdater(mock_session)
    await updater.mark_failed(document_id=doc_id, error_message=long_error)

    # Verify error was truncated
    call_args = mock_session.execute.call_args
    assert len(call_args[0][1]["error_msg"]) == 2000
