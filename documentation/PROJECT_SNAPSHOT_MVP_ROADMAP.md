# PROJECT SNAPSHOT & MVP ROADMAP

## Current Stage: "Functionally Working, Backend-to-RDS Ingestion"

**Date**: 2024-12-25
**Status**: Integrated document ingestion pipeline with Lambda, SQS, and S3. Document status is successfully updated in RDS.

---

## 1. Accomplishments (Current Processing Flow)

1. **Infrastructure**:
   - S3 Ingestion bucket triggers SQS upon document upload (`sessions/{session_id}/documents/{filename}`).
   - SQS Queue acts as a buffer and event source for the Lambda Processor.
   - Lambda Function (Image-based) is configured with VPC access to RDS and internal networking.
2. **Lambda Logic**:
   - **Event Parsing**: Robustly handles S3-wrapped SQS events and direct SQS messages.
   - **Persistence**: Automatically creates `documents` records in RDS with `PROCESSING` status upon receipt.
   - **Processing**: Executes `Parsing` -> `Chunking` -> `Embedding` -> `S3 Vector Store`.
   - **State Management**: Updates RDS status to `COMPLETED` on success or `FAILED` with error details on failure.
3. **Database Integration**:
   - `DocumentStatusUpdater` provides clean, async SQLAlchemy-based status management for Lambda.

---

## 2. Remaining Steps for MVP (Roadmap)

### Phase 1: Frontend Status Integration (Polling)

- **Problem**: The frontend currently "fires and forgets" the upload. It doesn't know when the document is ready for chatting.
- **Back-end Task**:
  - Implement/Expose a `GET /sessions/{session_id}/documents` endpoint in FastAPI.
  - This endpoint must return the `status` and `error_message` from the RDS `documents` table.
- **Front-end Task**:
  - Implement a polling mechanism (e.g., `useInterval` or `react-query` polling) in the Session View.
  - While a document is in `processing` or `pending` status, show a spinner or "Analyzing..." badge.
  - once status is `completed`, enable chat interaction for that document.
  - If status is `failed`, show the error message to the user.

### Phase 2: RAG Orchestration (Chat Integration)

- **Problem**: The Chat API currently searches local FAISS or doesn't yet fully integrate with the S3-based vector store created by Lambda.
- **Task**:
  - Update the Backend chat router to query the S3 Vector Store (or the corresponding vector database) using the `session_id` as a filter.
  - Ensure the chunks stored by Lambda are correctly retrieved and passed to the LLM context.

### Phase 3: Deployment & Polish

- **Task**:
  - **Environment parity**: Ensure `.env.production` reflects the AWS resources (RDS Host, S3 Buckets).
  - **Monitoring**: Add CloudWatch Alarms for Lambda failures and SQS Dead Letter Queue (DLQ).
  - **Aesthetics**: Polish the Document Management sidebar to show status icons (Green check for Ready, Red X for Failed, Blue pulse for Processing).

---

## 3. Risk Assessment

- **Lambda Retries**: SQS will retry failed messages. If a message fails due to code bugs, it might hit the DLQ. We need a way to clear/re-process these.
- **RDS Connections**: Ensure Lambda doesn't exhaust RDS connection pool under high load. Using `asyncio.run` in handler might create many engines if not careful (currently engines are created per-call or cached depending on context).

---

## 4. Resource Mapping

- **Tech Stack**: AWS (Lambda, SQS, S3, RDS), FastAPI, React, SQLAlchemy, Bedrock.
- **Source Code**:
  - `backend/core/document_processing/lambda_handler.py` (The Heart)
  - `backend/api/routers/documents.py` (The Status API - _needs update_)
  - `study-buddy-ai/src/hooks/useDocuments.ts` (The Polling Logic - _needs update_)
