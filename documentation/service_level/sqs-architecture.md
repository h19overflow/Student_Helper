# SQS Queue Architecture

Async document processing pipeline using AWS SQS.

## Overview

SQS (Simple Queue Service) decouples the backend from document processing. The backend queues tasks and returns immediately; Lambda processes asynchronously.

```mermaid
flowchart LR
    subgraph Backend[EC2 - FastAPI]
        API[API Endpoint]
        SVC[Document Service]
    end

    subgraph Queue[SQS]
        Q[(Main Queue)]
        DLQ[(Dead Letter Queue)]
    end

    subgraph Processor[Lambda]
        H[Handler]
        P[Doc Processor]
    end

    API --> SVC
    SVC -->|send_message| Q
    Q -->|trigger| H
    H --> P
    Q -->|3 failures| DLQ
```

## Why SQS?

| Problem | SQS Solution |
|---------|--------------|
| User waits for slow operation | Backend queues task, returns 202 immediately |
| Lambda is busy | Messages wait in queue until processed |
| Lambda crashes mid-task | Message reappears after visibility timeout |
| Poison messages | Dead Letter Queue (DLQ) catches repeated failures |

## Message Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Queued: Backend sends message

    Queued --> Invisible: Lambda picks up
    note right of Invisible: Visibility timeout (5 min)

    Invisible --> Deleted: Processing succeeds
    Deleted --> [*]

    Invisible --> Queued: Processing fails
    note left of Queued: Retry (up to 3x)

    Queued --> DeadLetterQueue: 3 consecutive failures
    DeadLetterQueue --> [*]: Manual investigation
```

## Queue Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Visibility Timeout | 300s (5 min) | 6x Lambda timeout (50s) |
| Message Retention | 4 days | Time to fix issues before loss |
| Receive Wait Time | 20s | Long polling reduces costs |
| Max Receive Count | 3 | Retries before sending to DLQ |
| Delay Seconds | 0 | Process immediately |

## Message Schema

**Document Processing Message:**

```json
{
  "job_id": "uuid",
  "session_id": "uuid",
  "documents": [
    {
      "document_id": "uuid",
      "s3_key": "sessions/{session_id}/docs/{filename}",
      "content_hash": "sha256",
      "file_type": "pdf"
    }
  ],
  "created_at": "ISO8601 timestamp"
}
```

**Message Attributes:**

| Attribute | Type | Purpose |
|-----------|------|---------|
| JobType | String | `document_ingestion` or `diagram_generation` |
| Priority | String | `high`, `normal`, `low` |

## Backend → SQS (Send)

The backend sends messages via boto3 through the VPC endpoint (no internet):

```python
# Pseudocode - actual implementation will follow project patterns
sqs_client.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps({
        "job_id": job_id,
        "session_id": session_id,
        "documents": [{"document_id": doc_id, "s3_key": key, ...}]
    }),
    MessageAttributes={
        "JobType": {"DataType": "String", "StringValue": "document_ingestion"}
    }
)
```

## SQS → Lambda (Receive)

Lambda is triggered automatically by SQS event source mapping:

```python
# Lambda handler receives batch of messages
def handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])

        job_id = body["job_id"]
        session_id = body["session_id"]

        for doc in body["documents"]:
            process_document(doc["s3_key"], doc["document_id"])

        update_job_status(job_id, "completed")
        # Success = SQS auto-deletes message
        # Exception = message returns to queue for retry
```

## IAM Permissions

**Backend (EC2) Policy:**

```json
{
  "Effect": "Allow",
  "Action": ["sqs:SendMessage"],
  "Resource": "arn:aws:sqs:{region}:{account}:doc-processing-queue"
}
```

**Lambda Policy:**

```json
{
  "Effect": "Allow",
  "Action": [
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:GetQueueAttributes"
  ],
  "Resource": "arn:aws:sqs:{region}:{account}:doc-processing-queue"
}
```

## End-to-End Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant API as FastAPI
    participant S3 as S3 Documents
    participant RDS as PostgreSQL
    participant SQS as SQS Queue
    participant L as Lambda
    participant Vec as S3 Vectors
    participant GCP as Google Embeddings

    U->>API: POST /sessions/{id}/documents
    API->>API: Validate files (size, type)
    API->>S3: Upload files
    API->>RDS: Create job (status: queued)
    API->>RDS: Create document records
    API->>SQS: Send message
    API-->>U: 202 Accepted + job_id

    Note over SQS,L: Async from here

    SQS->>L: Trigger with message batch
    L->>S3: Download file
    L->>L: Parse document
    L->>L: Chunk content
    L->>GCP: Generate embeddings
    GCP-->>L: Embedding vectors
    L->>Vec: Store vectors
    L->>RDS: Update job (completed/failed)

    U->>API: GET /jobs/{id}
    API->>RDS: Query job status
    API-->>U: Job status response
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| Lambda timeout | Message returns to queue, retry |
| Embedding API failure | Exponential backoff, then DLQ |
| Invalid file format | Mark job failed, no retry |
| S3 file missing | Mark job failed, log error |
| 3 consecutive failures | Move to DLQ, alert ops |

## Dead Letter Queue

```mermaid
flowchart TB
    subgraph MainQueue[Main Queue]
        M1[Message]
    end

    subgraph Processing
        L[Lambda]
        F1[Fail 1]
        F2[Fail 2]
        F3[Fail 3]
    end

    subgraph DLQ[Dead Letter Queue]
        D1[Failed Message]
        CW[CloudWatch Alarm]
        OPS[Ops Investigation]
    end

    M1 --> L
    L --> F1
    F1 -->|retry| L
    L --> F2
    F2 -->|retry| L
    L --> F3
    F3 -->|max receives exceeded| D1
    D1 --> CW
    CW -->|alert| OPS
    OPS -->|fix & replay| MainQueue
```

**DLQ Configuration:**

- Same message schema as main queue
- 14-day retention for debugging
- CloudWatch alarm on DLQ depth > 0
- Manual replay after fixing issues
