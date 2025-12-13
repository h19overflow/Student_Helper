# Product Requirements Document

## Product Overview

### Problem
Students want fast, accurate answers grounded in their own uploaded materials. They often need visual explanations (flows, architectures, processes) rather than plain text.

### Solution
A session-based Q&A backend where each chat session has its own retrieval scope. Supports batch uploads with non-blocking processing, returns citeable answers, and can generate diagrams on demand.

### Goals
- Grounded Q&A with citations from uploaded documents
- Non-blocking document ingestion (uploads return immediately)
- Full observability of all chat and ingestion operations
- Quality evaluation for regression tracking

### Non-Goals
- Authentication, authorization, billing
- Frontend UX polish (backend-first project)
- Multi-tenant security hardening

---

## Users & Use Cases

### Target Users
- University/college students uploading lecture slides, notes, and papers
- Students who want diagrams to visualize concepts, flows, or relationships

### Primary Use Cases
1. Upload multiple documents into a session and ask questions constrained to those docs
2. Scope retrieval to a specific document using @<doc> syntax
3. Request diagrams (flowchart, sequence diagram, class diagram) related to an answer

---

## Functional Requirements

### Sessions
- Create a session that stores chat history
- Each session tracks: document registry, upload/processing status, chat messages

### Document Upload
- Support batch upload of multiple documents
- Return immediately (non-blocking) while processing runs in background
- Provide job status endpoint to check processing progress

### Question Answering
- Search uploaded documents for relevant content
- Support filtering by session and optionally by specific document
- Return answers with citations (document name, page/section, source reference)

### Diagram Generation
- User can explicitly request a diagram
- Output includes diagram code and short description
- Diagrams should be grounded in retrieved context
- If not grounded, mark as "conceptual" or refuse

### Observability
- Trace every ingestion job and chat interaction
- Track: session, job, model, latency, retrieval parameters

### Evaluation
- Offline evaluation runner for quality regression tracking
- Load test datasets with questions, ground truth, and expected answers

---

## Non-Functional Requirements

### Performance
- Ingestion must be horizontally scalable
- Use batching for efficiency

### Reliability
- Idempotent ingestion (re-running won't duplicate data)
- Clear error handling for failed jobs

### Security (Baseline)
- Limit upload size and file types
- Sanitize filenames and user-provided names
- Prevent prompt injection from retrieved content

---

## Open Decisions
1. **Session isolation**: Separate storage per session vs shared storage with session filtering
2. **Diagram grounding**: Strictly require citations vs allow conceptual diagrams
3. **Evaluation cadence**: Automated nightly runs vs manual trigger
