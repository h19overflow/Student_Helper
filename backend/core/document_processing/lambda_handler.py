"""
Lambda handler for SQS-triggered document processing.

Processes documents uploaded to S3 through the ingestion pipeline:
parse → chunk → embed → upload to S3 Vectors → update RDS status.

Environment variables (to be configured):
- DOCUMENTS_BUCKET: S3 bucket for input documents
- VECTORS_BUCKET: S3 Vectors bucket name
- DATABASE_URL: PostgreSQL connection string
- AWS_REGION: AWS region
- LOG_LEVEL: Logging level

Dependencies: models.sqs_event, entrypoint, database
System role: Lambda entry point for async document ingestion
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict
from urllib.parse import unquote

from .models.sqs_event import SQSEventSchema
from .entrypoint import DocumentPipeline
from .database.document_status_updater import DocumentStatusUpdater, get_async_session_factory

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


class MessageParseError(Exception):
    """Raised when SQS message cannot be parsed."""

    pass


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""

    pass


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

    Args:
        record: SQS record containing S3 event

    Returns:
        SQSEventSchema: Standardized document metadata

    Raises:
        MessageParseError: Invalid S3 event format or missing fields
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
        # Expected format: documents/{session_id}/{filename}
        parts = s3_key.split("/")
        if len(parts) < 3 or parts[0] != "documents":
            raise ValueError(f"Invalid S3 key format: {s3_key}")

        session_id = parts[1]
        filename = "/".join(parts[2:])  # Handle filenames with slashes

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
            "%s:parse_s3_event_record - Parsed S3 event",
            __name__,
            extra={
                "message_id": record.get("messageId"),
                "document_id": str(message.document_id),
                "session_id": str(message.session_id),
                "s3_key": s3_key,
            },
        )
        return message

    except json.JSONDecodeError as e:
        logger.error("%s:parse_s3_event_record - JSONDecodeError: %s", __name__, e)
        raise MessageParseError(f"Invalid JSON in message body: {e}") from e
    except ValueError as e:
        logger.error("%s:parse_s3_event_record - ValueError: %s", __name__, e)
        raise MessageParseError(f"Invalid S3 event format: {e}") from e
    except Exception as e:
        logger.error("%s:parse_s3_event_record - %s: %s", __name__, type(e).__name__, e)
        raise MessageParseError(f"Failed to parse S3 event: {e}") from e


def parse_sqs_record(record: Dict[str, Any]) -> SQSEventSchema:
    """
    Parse and validate SQS record.

    Args:
        record: Single SQS record from event['Records']

    Returns:
        SQSEventSchema: Validated document metadata

    Raises:
        MessageParseError: Invalid message format or validation failed
    """
    try:
        # Extract message body (JSON string)
        message_body = record.get("body")
        if not message_body:
            raise ValueError("Empty message body")

        # Parse JSON and validate against schema
        message = SQSEventSchema.model_validate_json(message_body)
        logger.info(
            "%s:parse_sqs_record - Parsed message",
            __name__,
            extra={
                "message_id": record.get("messageId"),
                "document_id": str(message.document_id),
            },
        )
        return message

    except json.JSONDecodeError as e:
        logger.error("%s:parse_sqs_record - JSONDecodeError: %s", __name__, e)
        raise MessageParseError(f"Invalid JSON in message body: {e}") from e
    except ValueError as e:
        logger.error("%s:parse_sqs_record - ValueError: %s", __name__, e)
        raise MessageParseError(f"Invalid message schema: {e}") from e
    except Exception as e:
        logger.error("%s:parse_sqs_record - %s: %s", __name__, type(e).__name__, e)
        raise MessageParseError(f"Failed to parse message: {e}") from e


def validate_environment() -> Dict[str, str]:
    """
    Validate required environment variables.

    Returns:
        Dict with required env vars

    Raises:
        ValueError: Missing required environment variable
    """
    required_vars = [
        "DOCUMENTS_BUCKET",
        "VECTORS_BUCKET",
        "DATABASE_URL",
        "AWS_REGION",
    ]

    env_config = {}
    missing = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            env_config[var] = value

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    logger.info("%s:validate_environment - Environment validated", __name__)
    return env_config


async def _update_status_processing(document_id: str) -> None:
    """Update document status to PROCESSING in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.mark_processing(document_id)


async def _update_status_completed(document_id: str) -> None:
    """Update document status to COMPLETED in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.mark_completed(document_id)


async def _update_status_failed(document_id: str, error_message: str) -> None:
    """Update document status to FAILED in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.mark_failed(document_id, error_message)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for SQS document processing events.

    Processes each SQS record (document) sequentially.
    On validation errors, continues to next record (doesn't stop batch).
    On pipeline errors, returns partial failure.

    Args:
        event: SQS event with Records array
        context: Lambda context object

    Returns:
        Dict with statusCode and results array
    """
    logger.info(
        "handler - Received SQS event",
        extra={"record_count": len(event.get("Records", []))},
    )

    # Validate environment at start
    try:
        _env_config = validate_environment()  # noqa: F841
    except ValueError as e:
        logger.error("%s:handler - ValueError: %s", __name__, e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "results": []}),
        }

    results = []
    failed_count = 0

    # Process each SQS message
    for record in event.get("Records", []):
        message_id = record.get("messageId")
        try:
            # Parse S3 event from SQS message
            message = parse_s3_event_record(record)
            document_id = str(message.document_id)

            logger.info(
                "%s:handler - Processing document",
                __name__,
                extra={
                    "document_id": document_id,
                    "session_id": str(message.session_id),
                    "s3_key": message.s3_key,
                },
            )

            # Update status to PROCESSING before pipeline starts
            try:
                asyncio.run(_update_status_processing(document_id))
            except Exception as e:
                logger.error(
                    "%s:handler - Failed to update status to PROCESSING: %s: %s",
                    __name__,
                    type(e).__name__,
                    e,
                    extra={"document_id": document_id},
                )
                raise DocumentProcessingError(f"Failed to update status to PROCESSING: {e}") from e

            # Initialize pipeline (done once, reused for all records)
            if not hasattr(handler, "_pipeline"):
                handler._pipeline = DocumentPipeline()

            pipeline = handler._pipeline

            # Process document through pipeline
            try:
                pipeline_result = pipeline.process(
                    s3_key=message.s3_key,
                    document_id=document_id,
                    session_id=str(message.session_id),
                )

                logger.info(
                    "%s:handler - Document processed successfully",
                    __name__,
                    extra={
                        "document_id": document_id,
                        "chunk_count": pipeline_result.chunk_count,
                        "processing_time_ms": pipeline_result.processing_time_ms,
                    },
                )

            except Exception as e:
                logger.error(
                    "%s:handler - %s: %s",
                    __name__,
                    type(e).__name__,
                    e,
                    extra={"document_id": document_id},
                )
                raise DocumentProcessingError(f"Pipeline processing failed: {e}") from e

            # Update status to COMPLETED after successful processing
            try:
                asyncio.run(_update_status_completed(document_id))
            except Exception as e:
                logger.error(
                    "%s:handler - Failed to update status to COMPLETED: %s: %s",
                    __name__,
                    type(e).__name__,
                    e,
                    extra={"document_id": document_id},
                )
                raise DocumentProcessingError(f"Failed to update status to COMPLETED: {e}") from e

            results.append(
                {
                    "messageId": message_id,
                    "status": "success",
                    "document_id": document_id,
                    "chunk_count": pipeline_result.chunk_count,
                    "processing_time_ms": pipeline_result.processing_time_ms,
                }
            )

        except MessageParseError as e:
            logger.warning("%s:handler - MessageParseError: %s", __name__, e)
            failed_count += 1
            results.append(
                {
                    "messageId": message_id,
                    "status": "failed",
                    "error": "Invalid message format",
                    "details": str(e),
                }
            )
            # Continue to next record, don't fail batch

        except DocumentProcessingError as e:
            logger.error("%s:handler - DocumentProcessingError: %s", __name__, e)
            failed_count += 1

            # Update status to FAILED in database
            try:
                # Extract document_id if available (from message parsed earlier)
                if "message" in dir() and message is not None:
                    asyncio.run(_update_status_failed(str(message.document_id), str(e)))
            except Exception as db_error:
                logger.error(
                    "%s:handler - Failed to update status to FAILED: %s: %s",
                    __name__,
                    type(db_error).__name__,
                    db_error,
                )

            results.append(
                {
                    "messageId": message_id,
                    "status": "failed",
                    "error": "Document processing failed",
                    "details": str(e),
                }
            )

        except Exception as e:
            logger.error("%s:handler - %s: %s", __name__, type(e).__name__, e)
            failed_count += 1
            results.append(
                {
                    "messageId": message_id,
                    "status": "failed",
                    "error": "Unexpected error",
                    "details": str(e),
                }
            )

    # Return 200 even with partial failures (Lambda won't retry failed messages)
    status_code = 200 if failed_count == 0 else 206
    logger.info(
        "%s:handler - Processing complete",
        __name__,
        extra={"success_count": len(results) - failed_count, "failed_count": failed_count},
    )

    return {
        "statusCode": status_code,
        "body": json.dumps(
            {
                "processed": len(results),
                "failed": failed_count,
                "results": results,
            }
        ),
    }
