# Lambda Document Processor Architecture

Single-purpose Lambda for document processing and vector insertion.

## Responsibility Boundary

```mermaid
flowchart TB
    subgraph Legend[Legend]
        L1[Lambda responsibility]:::lambda
        L2[Backend responsibility]:::backend
    end

    subgraph Backend[EC2 - FastAPI Backend]
        DS[Document Service]
        RS[RAG Service]
        SS[Session Service]

        DS -->|upload| UploadOp[Create vectors]:::lambda
        RS -->|query| QueryOp[Retrieve vectors]:::backend
        RS -->|delete| DeleteOp[Delete vectors]:::backend
        SS -->|cascade| CascadeOp[Delete session vectors]:::backend
    end

    subgraph Lambda[Lambda - Doc Processor]
        LP[Process & Insert ONLY]:::lambda
    end

    subgraph S3Vec[S3 Vectors]
        VDB[(Vector Store)]
    end

    UploadOp -->|SQS| LP
    LP -->|write| VDB

    QueryOp -->|direct| VDB
    DeleteOp -->|direct| VDB
    CascadeOp -->|direct| VDB

    classDef lambda fill:#22c55e,stroke:#16a34a,color:#ffffff
    classDef backend fill:#3b82f6,stroke:#2563eb,color:#ffffff
```

**Lambda scope:** Process documents → Generate embeddings → Insert vectors

**Backend scope:** Query, delete, cascade delete, all other vector operations

## Why This Separation?

| Concern | Lambda | Backend |
|---------|--------|---------|
| Document parsing | Yes | No |
| Chunking | Yes | No |
| Embedding generation | Yes | No |
| Vector insertion | Yes | No |
| Vector querying | No | Yes |
| Vector deletion | No | Yes |
| Session management | No | Yes |
| User-facing API | No | Yes |

**Rationale:**
- Lambda optimized for CPU/memory-intensive parsing
- Backend handles real-time user requests
- Clear ownership prevents coupling
- Easier to scale independently

## Communication Flow

```mermaid
sequenceDiagram
    participant API as FastAPI Backend
    participant SQS as SQS Queue
    participant L as Lambda
    participant S3D as S3 Documents
    participant GCP as Google Embeddings
    participant S3V as S3 Vectors
    participant RDS as PostgreSQL

    Note over API,SQS: Backend initiates (fire-and-forget)
    API->>SQS: send_message(job_id, docs)
    API-->>API: Return 202 to user

    Note over SQS,L: SQS triggers Lambda
    SQS->>L: Invoke with message batch

    Note over L,S3V: Lambda processes (isolated)
    L->>S3D: Download source file
    S3D-->>L: File content
    L->>L: Parse document
    L->>L: Chunk content
    L->>GCP: Batch embed chunks
    GCP-->>L: Embedding vectors
    L->>S3V: Insert vectors with metadata
    L->>RDS: Update job status

    Note over L,RDS: No response to backend
```

## Lambda Internal Architecture

```mermaid
flowchart TB
    subgraph Handler[Lambda Handler]
        E[Event Parser]
    end

    subgraph Pipeline[Processing Pipeline]
        direction TB
        DL[Downloader]
        P[Parser]
        C[Chunker]
        EM[Embedder]
        I[Inserter]
    end

    subgraph Clients[External Clients]
        S3C[S3 Client]
        GCPC[Embedding Client]
        VEC[Vector Client]
        DBC[Database Client]
    end

    E --> DL
    DL --> P
    P --> C
    C --> EM
    EM --> I

    DL --> S3C
    EM --> GCPC
    I --> VEC
    I --> DBC
```

## Pipeline Stages

### 1. Event Parser

Extracts job details from SQS event:

```python
# Input: SQS event with batch of messages
{
    "Records": [
        {
            "body": {
                "job_id": "uuid",
                "session_id": "uuid",
                "documents": [...]
            }
        }
    ]
}
```

### 2. Downloader

- Fetches file from S3 Documents bucket
- Validates file exists and matches expected hash
- Streams large files to avoid memory issues

### 3. Parser

- Extracts text from file based on type
- Supported formats: PDF, DOCX, TXT, MD
- Preserves structure metadata (pages, sections)

### 4. Chunker

- Applies chunking strategy based on document type
- Generates deterministic chunk IDs (content hash)
- Preserves parent-child relationships

### 5. Embedder

- Batches chunks for efficient API calls
- Calls Google text-embedding-004
- Handles rate limits with exponential backoff

### 6. Inserter

- Writes vectors to S3 Vectors with metadata
- Updates document record in RDS
- Updates job status (completed/failed)

## Vector Metadata Schema

Each vector stored with metadata for retrieval:

```json
{
  "vector_id": "chunk_content_hash",
  "session_id": "uuid",
  "document_id": "uuid",
  "chunk_index": 0,
  "content": "chunk text content",
  "metadata": {
    "page_number": 1,
    "section": "Introduction",
    "parent_chunk_id": "optional",
    "source_file": "document.pdf"
  },
  "embedding": [0.1, 0.2, ...]
}
```

## Error Handling

```mermaid
flowchart TB
    Start[Process Document] --> Parse{Parse OK?}

    Parse -->|Yes| Chunk{Chunk OK?}
    Parse -->|No| ParseErr[Log error]
    ParseErr --> MarkFailed

    Chunk -->|Yes| Embed{Embed OK?}
    Chunk -->|No| ChunkErr[Log error]
    ChunkErr --> MarkFailed

    Embed -->|Yes| Insert{Insert OK?}
    Embed -->|Rate limit| Retry[Exponential backoff]
    Retry --> Embed
    Embed -->|No| EmbedErr[Log error]
    EmbedErr --> Throw[Throw exception]

    Insert -->|Yes| MarkComplete[Update job: completed]
    Insert -->|No| InsertErr[Log error]
    InsertErr --> Throw

    Throw --> SQSRetry[SQS retry mechanism]
    MarkFailed[Update job: failed]
    MarkComplete --> Done[Success]
    MarkFailed --> Done
```

**Error categories:**

| Error Type | Retryable | Action |
|------------|-----------|--------|
| Parse failure | No | Mark job failed, skip |
| Chunk failure | No | Mark job failed, skip |
| Embedding API rate limit | Yes | Exponential backoff |
| Embedding API error | Yes | Throw, let SQS retry |
| Vector insert error | Yes | Throw, let SQS retry |
| S3 download error | Yes | Throw, let SQS retry |

## Lambda Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Runtime | Python 3.12 | Latest stable |
| Memory | 1024 MB | PDF parsing needs RAM |
| Timeout | 50 seconds | Allows 6 retries in visibility window |
| Reserved concurrency | 10 | Prevent embedding API overload |
| Batch size | 10 | Messages per invocation |

## IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::docs-bucket/sessions/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::vectors-bucket/sessions/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:{region}:{account}:doc-processing-queue"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:{region}:{account}:secret:api-keys-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds-db:connect"
      ],
      "Resource": "arn:aws:rds-db:{region}:{account}:dbuser:*/lambda_user"
    }
  ]
}
```

## What Lambda Does NOT Do

| Operation | Why Not |
|-----------|---------|
| Vector retrieval | Real-time, user-facing → Backend |
| Vector deletion | Tied to session lifecycle → Backend |
| Chat history | User context → Backend |
| Session management | User-facing API → Backend |
| Health checks | ALB target → Backend |
| Streaming responses | SSE to client → Backend |

## Idempotency

Lambda must handle duplicate messages (at-least-once delivery):

1. **Check before insert:** Query vector store for existing chunk_id
2. **Skip if exists:** Same content hash = same vectors
3. **Upsert pattern:** Overwrite if re-processing needed
4. **Job status:** Only update if current status allows transition

```mermaid
flowchart LR
    Msg[Message received] --> Check{Chunk exists?}
    Check -->|Yes, same hash| Skip[Skip insertion]
    Check -->|Yes, different hash| Upsert[Overwrite vectors]
    Check -->|No| Insert[Insert new vectors]

    Skip --> Next[Next chunk]
    Upsert --> Next
    Insert --> Next
```
