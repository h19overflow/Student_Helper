# Document Processing Lambda

Standalone Lambda container for document ingestion pipeline.

## Overview

This module provides a containerized Lambda function that processes documents through the following pipeline:
1. **Parsing** - Extract text from PDF/DOCX using Docling
2. **Chunking** - Split documents into retrievable chunks
3. **Embedding** - Generate vectors using Amazon Titan Embeddings v2 (1536 dimensions)
4. **Indexing** - Upload to S3 Vectors for similarity search
5. **Status Update** - Update document status in RDS

## Architecture

```
SQS Event → Lambda Handler → DocumentPipeline → S3 Vectors
                                    ↓
                                  RDS Status Update
```

## Build Docker Image

```bash
cd backend/core/document_processing
docker build -t doc-processor-lambda .
```

## Test Locally (Optional)

```bash
# Run container
docker run -p 9000:8080 doc-processor-lambda

# Send test event
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
    "Records": [
      {
        "body": "{\"document_id\": \"...\", \"session_id\": \"...\", \"s3_bucket\": \"...\", \"s3_key\": \"...\", \"filename\": \"...\"}"
      }
    ]
  }'
```

## Push to ECR

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag doc-processor-lambda:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/student-helper-doc-processor:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/student-helper-doc-processor:latest
```

## Environment Variables

Configure these in Lambda or Pulumi:

| Variable | Description | Example |
|----------|-------------|---------|
| `DOC_PIPELINE_VECTORS_BUCKET` | S3 Vectors bucket name | `student-helper-dev-vectors` |
| `DOC_PIPELINE_BEDROCK_REGION` | AWS region for Bedrock | `us-east-1` |
| `DOC_PIPELINE_EMBEDDING_MODEL_ID` | Bedrock model ID | `amazon.titan-embed-text-v2:0` |
| `DOC_PIPELINE_DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `DOC_PIPELINE_CHUNK_SIZE` | Max chunk size in characters | `1000` |
| `DOC_PIPELINE_CHUNK_OVERLAP` | Chunk overlap | `200` |
| `AWS_REGION` | Lambda region | `us-east-1` |
| `LOG_LEVEL` | Logging level | `INFO` |

## SQS Message Format

Expected message structure:

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "s3_bucket": "student-helper-dev-documents",
  "s3_key": "uploads/2024/01/document.pdf",
  "filename": "document.pdf"
}
```

## IAM Permissions Required

The Lambda execution role needs:

- **S3**: `s3:GetObject` on documents bucket
- **S3 Vectors**: `s3vectors:*` on vectors bucket
- **Bedrock**: `bedrock:InvokeModel` for Titan Embeddings
- **RDS**: VPC access to PostgreSQL database
- **SQS**: `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`
- **Secrets Manager**: `secretsmanager:GetSecretValue` (if using secrets)
- **CloudWatch Logs**: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

## Dependencies

See [requirements.txt](requirements.txt) for full list. Key dependencies:

- `docling>=2.15.2` - Document parsing
- `langchain>=1.1.3` - Text processing
- `langchain-aws>=0.2.10` - Bedrock embeddings
- `boto3>=1.35.81` - AWS SDK
- `sqlalchemy>=2.0.36` - Database ORM
- `pydantic>=2.10.0` - Data validation

## Integration Points (TODO)

The following integration points are scaffolded and need implementation:

1. **S3 Download** - Download document from S3 to `/tmp` (see: [lambda_handler.py:53](lambda_handler.py#L53))
2. **S3 Vectors Upload** - Implement upsert logic (see: [tasks/vector_store_task.py:51](tasks/vector_store_task.py#L51))
3. **RDS Status Update** - Update DocumentModel status (see: [lambda_handler.py:61](lambda_handler.py#L61))
4. **Bedrock Credentials** - Configure IAM role or credentials (see: [tasks/embedding_task.py:45](tasks/embedding_task.py#L45))
5. **Error Handling** - Update RDS on failure (see: [lambda_handler.py:67](lambda_handler.py#L67))

## Deployment with Pulumi

Update your Pulumi stack:

```python
# IAC/components/compute/lambda_processor.py
lambda_function = aws.lambda_.Function(
    "doc-processor",
    image_uri=f"{ecr_repository.repository_url}:latest",
    package_type="Image",
    role=lambda_role.arn,
    vpc_config=vpc_config,
    environment={
        "variables": {
            "DOC_PIPELINE_VECTORS_BUCKET": vectors_bucket.id,
            "DOC_PIPELINE_DATABASE_URL": database_url,
            # ... other env vars
        }
    },
    timeout=300,
    memory_size=512,
)

# SQS event source
event_source = aws.lambda_.EventSourceMapping(
    "doc-processor-sqs",
    event_source_arn=sqs_queue.arn,
    function_name=lambda_function.name,
    batch_size=1,
)
```

## Monitoring

Key CloudWatch metrics to monitor:

- **Duration** - Processing time per document
- **Errors** - Failed invocations
- **Throttles** - Rate limiting issues
- **DeadLetterErrors** - DLQ deliveries

## Troubleshooting

### Import Errors
Ensure all dependencies are in `requirements.txt` and rebuild the image.

### Timeout Errors
Increase Lambda timeout (max 15 minutes) or optimize chunking parameters.

### Out of Memory
Increase Lambda memory (max 10 GB) or process smaller documents.

### VPC Connectivity
Ensure Lambda security group allows outbound to RDS and VPC endpoints for Bedrock/S3.

## Project Structure

```
backend/core/document_processing/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Lambda container image
├── lambda_handler.py            # Lambda entry point
├── configs.py                   # Environment settings
├── entrypoint.py                # DocumentPipeline orchestrator
├── models/
│   ├── chunk.py                 # Chunk data model
│   ├── pipeline_result.py       # Pipeline result model
│   └── sqs_event.py             # SQS message schema
└── tasks/
    ├── parsing_task.py          # PDF/DOCX parsing (Docling)
    ├── chunking_task.py         # Text splitting
    ├── embedding_task.py        # Bedrock Titan embeddings
    └── vector_store_task.py     # S3 Vectors upload (scaffold)
```

## Notes

- **This is scaffolding** - Integration details (DB connections, S3 Vectors API, Bedrock auth) need implementation
- All TODO comments mark integration points for future work
- Focus is on modular structure and smooth dependency installation
- Package designed to be self-contained and deployable to Lambda
