# Data Flow Architecture

Component-level data flows for document upload, processing, and query operations.

## Flow Diagram

```mermaid
flowchart LR
    subgraph Upload[Document Upload Flow]
        A1[POST /upload] --> A2[Validate File]
        A2 --> A3[Store in S3]
        A3 --> A4[Create Job Record]
        A4 --> A5[Send SQS Message]
        A5 --> A6[Return job_id]
    end

    subgraph Process[Background Processing - Lambda]
        B1[SQS Trigger] --> B2[Download from S3]
        B2 --> B3[Extract Text]
        B3 --> B4[Chunk Text]
        B4 --> B5[Get Embeddings]
        B5 --> B6[Store in S3 Vectors]
        B6 --> B7[Update Job Status]
    end

    subgraph Query[Question Answering Flow]
        C1[POST /ask] --> C2[Embed Question]
        C2 --> C3[Query S3 Vectors]
        C3 --> C4[Get Top-K Chunks]
        C4 --> C5[Build Prompt]
        C5 --> C6[Call Claude]
        C6 --> C7[Format Citations]
        C7 --> C8[Return Answer]
    end
```

## Flow Descriptions

### Document Upload Flow

1. **POST /upload** - User submits document via API
2. **Validate File** - Check file type, size limits
3. **Store in S3** - Upload to documents bucket
4. **Create Job Record** - Insert pending job in RDS
5. **Send SQS Message** - Queue processing task
6. **Return job_id** - Client receives tracking ID

### Background Processing Flow

1. **SQS Trigger** - Lambda invoked by queue message
2. **Download from S3** - Fetch document from bucket
3. **Extract Text** - Parse PDF content
4. **Chunk Text** - Split into semantic chunks
5. **Get Embeddings** - Call Google text-embedding-004 (3072 dims)
6. **Store in S3 Vectors** - Index vectors for retrieval
7. **Update Job Status** - Mark job complete in RDS

### Question Answering Flow

1. **POST /ask** - User submits question
2. **Embed Question** - Convert query to vector via Google Embeddings
3. **Query S3 Vectors** - Similarity search
4. **Get Top-K Chunks** - Retrieve relevant context
5. **Build Prompt** - Construct LLM prompt with context
6. **Call Claude** - Generate answer
7. **Format Citations** - Add source references
8. **Return Answer** - Respond with cited answer
