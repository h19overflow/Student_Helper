# Service Architecture

Internal service components for EC2 backend and Lambda processor.

## Service Diagram

```mermaid
flowchart TB
    subgraph ec2_service[EC2 - FastAPI Backend]
        FastAPI[FastAPI App]
        SessionMgr[Session Manager]
        DocMgr[Document Manager]
        Retriever[Retriever]
        Generator[Answer Generator]

        FastAPI --> SessionMgr
        FastAPI --> DocMgr
        FastAPI --> Retriever
        FastAPI --> Generator
    end

    subgraph lambda_service[Lambda - Document Processor]
        Handler[Lambda Handler]
        Extractor[PDF Extractor]
        Chunker[Text Chunker]
        Embedder[Embedding Client]
        Indexer[S3 Vectors Client]

        Handler --> Extractor
        Extractor --> Chunker
        Chunker --> Embedder
        Embedder --> Indexer
    end

    subgraph managed[Managed Services]
        RDS[(RDS PostgreSQL)]
        S3[(S3 Buckets)]
        S3Vec[(S3 Vectors)]
        SQS[SQS]
    end

    ec2_service --> RDS
    ec2_service --> S3
    ec2_service --> S3Vec
    ec2_service --> SQS

    SQS --> lambda_service
    lambda_service --> S3
    lambda_service --> S3Vec
    lambda_service --> RDS
```

## EC2 Backend Components

| Component | Responsibility |
|-----------|----------------|
| FastAPI App | HTTP routing, request handling |
| Session Manager | Session CRUD, state management |
| Document Manager | Upload handling, job creation |
| Retriever | Vector search, context retrieval |
| Answer Generator | Prompt building, LLM calls, citations |

## Lambda Processor Components

| Component | Responsibility |
|-----------|----------------|
| Handler | SQS event parsing, orchestration |
| PDF Extractor | Text extraction from documents |
| Text Chunker | Semantic chunking |
| Embedding Client | Google text-embedding-004 API calls |
| S3 Vectors Client | Vector indexing and storage |

## Managed Services

| Service | Purpose |
|---------|---------|
| RDS PostgreSQL | Persistent data (sessions, jobs, metadata) |
| S3 Buckets | Document and static file storage |
| S3 Vectors | Vector embedding storage and retrieval |
| SQS | Async job queue with DLQ |
