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

Dependencies: models.sqs_event, entrypoint
System role: Lambda entry point for async document ingestion
"""

import json
import logging
import os
from typing import Any, Dict

from .models.sqs_event import SQSEventSchema
from .entrypoint import DocumentPipeline

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


class MessageParseError(Exception):
    """Raised when SQS message cannot be parsed."""

    pass


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""

    pass


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
            f"{__name__}:parse_sqs_record - Parsed message",
            extra={
                "message_id": record.get("messageId"),
                "document_id": str(message.document_id),
            },
        )
        return message

    except json.JSONDecodeError as e:
        logger.error(f"{__name__}:parse_sqs_record - JSONDecodeError: {e}")
        raise MessageParseError(f"Invalid JSON in message body: {e}") from e
    except ValueError as e:
        logger.error(f"{__name__}:parse_sqs_record - ValueError: {e}")
        raise MessageParseError(f"Invalid message schema: {e}") from e
    except Exception as e:
        logger.error(f"{__name__}:parse_sqs_record - {type(e).__name__}: {e}")
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

    logger.info(f"{__name__}:validate_environment - Environment validated")
    return env_config


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
        f"{__name__}:handler - Received SQS event",
        extra={"record_count": len(event.get("Records", []))},
    )

    # Validate environment at start
    try:
        _env_config = validate_environment()  # Will be used in Stage 3
    except ValueError as e:
        logger.error(f"{__name__}:handler - ValueError: {e}")
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
            # Parse and validate SQS message
            message = parse_sqs_record(record)

            logger.info(
                f"{__name__}:handler - Processing document",
                extra={
                    "document_id": str(message.document_id),
                    "session_id": str(message.session_id),
                    "s3_key": message.s3_key,
                },
            )

            # Initialize pipeline (done once, reused for all records)
            if not hasattr(handler, "_pipeline"):
                handler._pipeline = DocumentPipeline()

            pipeline = handler._pipeline

            # Process document through pipeline
            try:
                pipeline_result = pipeline.process(
                    s3_key=message.s3_key,
                    document_id=str(message.document_id),
                    session_id=str(message.session_id),
                )

                logger.info(
                    f"{__name__}:handler - Document processed successfully",
                    extra={
                        "document_id": str(message.document_id),
                        "chunk_count": pipeline_result.chunk_count,
                        "processing_time_ms": pipeline_result.processing_time_ms,
                    },
                )

            except Exception as e:
                logger.error(
                    f"{__name__}:handler - {type(e).__name__}: {e}",
                    extra={"document_id": str(message.document_id)},
                )
                raise DocumentProcessingError(f"Pipeline processing failed: {e}") from e

            # TODO (Stage 4): Update RDS document status to PROCESSING

            results.append(
                {
                    "messageId": message_id,
                    "status": "success",
                    "document_id": str(message.document_id),
                    "chunk_count": pipeline_result.chunk_count,
                    "processing_time_ms": pipeline_result.processing_time_ms,
                }
            )

        except MessageParseError as e:
            logger.warning(f"{__name__}:handler - MessageParseError: {e}")
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
            logger.error(f"{__name__}:handler - DocumentProcessingError: {e}")
            failed_count += 1
            # TODO (Stage 4): Update RDS document status to FAILED
            results.append(
                {
                    "messageId": message_id,
                    "status": "failed",
                    "error": "Document processing failed",
                    "details": str(e),
                }
            )

        except Exception as e:
            logger.error(f"{__name__}:handler - {type(e).__name__}: {e}")
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
        f"{__name__}:handler - Processing complete",
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
