"""Unit tests for SQS event schema validation."""

import pytest
import json
from uuid import uuid4
from backend.core.document_processing.models.sqs_event import (
    SQSEventSchema,
    SQSEvent,
    SQSRecord,
)


def test_sqs_event_schema_valid():
    """Test valid SQS event schema."""
    doc_id = uuid4()
    session_id = uuid4()

    schema = SQSEventSchema(
        document_id=doc_id,
        session_id=session_id,
        s3_key="documents/session_id/file.pdf",
        filename="file.pdf",
        file_size_bytes=1024,
    )

    assert str(schema.document_id) == str(doc_id)
    assert str(schema.session_id) == str(session_id)
    assert schema.s3_key == "documents/session_id/file.pdf"
    assert schema.filename == "file.pdf"
    assert schema.file_size_bytes == 1024


def test_sqs_event_schema_from_json():
    """Test parsing SQS event from JSON."""
    json_body = json.dumps({
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": "550e8400-e29b-41d4-a716-446655440001",
        "s3_key": "documents/550e8400-e29b-41d4-a716-446655440001/resume.pdf",
        "filename": "resume.pdf",
        "file_size_bytes": 1024000,
    })

    schema = SQSEventSchema.model_validate_json(json_body)
    assert schema.filename == "resume.pdf"
    assert schema.file_size_bytes == 1024000


def test_sqs_event_schema_missing_field():
    """Test validation error on missing required field."""
    with pytest.raises(ValueError):
        SQSEventSchema(
            document_id=uuid4(),
            # Missing session_id
            s3_key="documents/session_id/file.pdf",
            filename="file.pdf",
            file_size_bytes=1024,
        )


def test_sqs_record_valid():
    """Test valid SQS record."""
    body = json.dumps({
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": "550e8400-e29b-41d4-a716-446655440001",
        "s3_key": "documents/550e8400-e29b-41d4-a716-446655440001/resume.pdf",
        "filename": "resume.pdf",
        "file_size_bytes": 1024000,
    })

    record = SQSRecord(
        messageId="msg-123",
        receiptHandle="receipt-handle-123",
        body=body,
        attributes={},
        md5OfBody="hash",
    )

    # Parse the body to validate it contains valid SQSEventSchema
    message = SQSEventSchema.model_validate_json(record.body)
    assert message.document_id


def test_sqs_event_full():
    """Test complete SQS event with multiple records."""
    body1 = json.dumps({
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": "550e8400-e29b-41d4-a716-446655440001",
        "s3_key": "documents/550e8400-e29b-41d4-a716-446655440001/resume.pdf",
        "filename": "resume.pdf",
        "file_size_bytes": 1024000,
    })

    body2 = json.dumps({
        "document_id": "550e8400-e29b-41d4-a716-446655440002",
        "session_id": "550e8400-e29b-41d4-a716-446655440003",
        "s3_key": "documents/550e8400-e29b-41d4-a716-446655440003/cover_letter.pdf",
        "filename": "cover_letter.pdf",
        "file_size_bytes": 512000,
    })

    event = SQSEvent(
        Records=[
            SQSRecord(
                messageId="msg-1",
                receiptHandle="receipt-1",
                body=body1,
                attributes={},
                md5OfBody="hash1",
            ),
            SQSRecord(
                messageId="msg-2",
                receiptHandle="receipt-2",
                body=body2,
                attributes={},
                md5OfBody="hash2",
            ),
        ]
    )

    assert len(event.Records) == 2
    msg1 = SQSEventSchema.model_validate_json(event.Records[0].body)
    msg2 = SQSEventSchema.model_validate_json(event.Records[1].body)
    assert msg1.filename == "resume.pdf"
    assert msg2.filename == "cover_letter.pdf"
