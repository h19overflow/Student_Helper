"""
SQS and S3 event parsing utilities for Lambda.
"""

import json
import logging
import uuid
from typing import Any, Dict
from urllib.parse import unquote

from backend.core.document_processing.models.sqs_event import SQSEventSchema
from backend.core.document_processing.lambda_utils.exceptions import MessageParseError

logger = logging.getLogger(__name__)


def parse_s3_event_record(record: Dict[str, Any]) -> SQSEventSchema:
    """
    Parse S3 event from SQS record.

    S3 sends event notifications to SQS with this structure:
    {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "bucket-name"},
                "object": {"key": "documents/session-id/filename.pdf", "size": 1024}
            }
        }]
    }

    Extracts session_id from S3 key path (documents/{session_id}/{filename}).
    """
    try:
        # Extract S3 event from message body
        message_body = record.get("body")
        if not message_body:
            raise ValueError("Empty message body")

        s3_event = json.loads(message_body)

        # Handle wrapped S3 events (from S3 → SQS notification)
        if "Records" in s3_event:
            # S3 event wrapped in Records array
            s3_records = s3_event.get("Records", [])
            if not s3_records:
                raise ValueError("No S3 records in event")
            s3_record = s3_records[0]
        else:
            # Direct S3 record
            s3_record = s3_event

        # Extract bucket and object info
        if s3_record.get("eventSource") != "aws:s3":
            raise ValueError(f"Invalid event source: {s3_record.get('eventSource')}")

        s3_info = s3_record.get("s3", {})
        object_info = s3_info.get("object", {})

        s3_key = unquote(object_info.get("key", ""))  # URL-decode the key
        file_size = object_info.get("size", 0)

        if not s3_key:
            raise ValueError("Missing S3 object key")

        # Extract session_id and filename from S3 key path
        # Format 1 (New): sessions/{session_id}/documents/{filename}
        # Format 2 (Legacy): documents/{session_id}/{filename}
        parts = s3_key.split("/")

        if len(parts) >= 4 and parts[0] == "sessions" and parts[2] == "documents":
            session_id = parts[1]
            filename = "/".join(parts[3:])
        elif len(parts) >= 3 and parts[0] == "documents":
            session_id = parts[1]
            filename = "/".join(parts[2:])
        else:
            raise MessageParseError(f"Skipping non-document object: {s3_key}")

        # Validate session_id is a valid UUID
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError as e:
            raise ValueError(f"Invalid session ID format: {session_id}") from e

        # Generate document_id (S3 events don't contain this)
        document_id = uuid.uuid4()

        message = SQSEventSchema(
            document_id=document_id,
            session_id=session_uuid,
            s3_key=s3_key,
            filename=filename,
            file_size_bytes=file_size,
        )

        logger.info(
            "parse_s3_event_record - Parsed S3 event",
            extra={
                "message_id": record.get("messageId"),
                "document_id": str(message.document_id),
                "session_id": str(message.session_id),
                "s3_key": s3_key,
            },
        )
        return message

    except json.JSONDecodeError as e:
        logger.error("parse_s3_event_record - JSONDecodeError: %s", e)
        raise MessageParseError(f"Invalid JSON in message body: {e}") from e
    except ValueError as e:
        logger.error("parse_s3_event_record - ValueError: %s", e)
        raise MessageParseError(f"Invalid S3 event format: {e}") from e
    except Exception as e: # pylint: disable=broad-except
        logger.error("parse_s3_event_record - %s: %s", type(e).__name__, e)
        raise MessageParseError(f"Failed to parse S3 event: {e}") from e


def parse_sqs_record(record: Dict[str, Any]) -> SQSEventSchema:
    """
    Parse and validate SQS record.
    """
    try:
        # Extract message body (JSON string)
        message_body = record.get("body")
        if not message_body:
            raise ValueError("Empty message body")

        # Parse JSON and validate against schema
        message = SQSEventSchema.model_validate_json(message_body)
        logger.info(
            "parse_sqs_record - Parsed message",
            extra={
                "message_id": record.get("messageId"),
                "document_id": str(message.document_id),
            },
        )
        return message

    except json.JSONDecodeError as e:
        logger.error("parse_sqs_record - JSONDecodeError: %s", e)
        raise MessageParseError(f"Invalid JSON in message body: {e}") from e
    except ValueError as e:
        logger.error("parse_sqs_record - ValueError: %s", e)
        raise MessageParseError(f"Invalid message schema: {e}") from e
    except Exception as e: # pylint: disable=broad-except
        logger.error("parse_sqs_record - %s: %s", type(e).__name__, e)
        raise MessageParseError(f"Failed to parse message: {e}") from e
