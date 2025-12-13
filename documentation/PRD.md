Below is a PRD for your student-focused RAG app (Q&A + Mermaid diagrams via “nano banana”), aligned to the stack you described (FastAPI, LangChain/LangGraph, Celery+RabbitMQ, S3 Vectors, Gemini embeddings, Postgres chat history, Langfuse, Ragas). S3 Vectors metadata filtering is a first-class requirement because it enables per-session/per-doc retrieval constraints and citations.​

Product overview
Problem
Students want fast, accurate answers grounded in their own uploaded materials, and they often need visual explanations (flows, architectures, processes) rather than plain text. (No auth; optimized for backend quality, async ingestion, and traceability.)

Solution
A session-based RAG backend where each chat session has its own retrieval scope (documents + chat history), supports batch uploads with non-blocking processing, returns citeable answers, and can generate Mermaid diagrams (“nano banana”) on demand as a companion output.

Goals
Grounded Q&A with citations from uploaded docs.​

Non-blocking ingestion: uploads return immediately; processing runs via Celery workers (RabbitMQ broker).​

Full observability: every chat + ingestion job traced in Langfuse (self-hosted via Docker Compose).​

Quantitative quality evaluation: Ragas evaluation runs on curated datasets for regression tracking.​

Non-goals
Authentication, authorization, billing, academic integrity enforcement, identity verification.

Frontend UX polish (basic UI acceptable; backend-first).

Multi-tenant security hardening (still do basic safety defaults, but not enterprise-grade).

Users & use cases
Target users
University/college students uploading lecture slides/notes/papers and asking questions grounded in them.

Students who want diagrams (Mermaid) to visualize concepts, flows, or relationships.

Primary use cases
Upload multiple documents into a session and ask questions constrained to those docs.

Use @<doc> to scope retrieval to one uploaded document (or a subset).​

Ask for a Mermaid diagram (flowchart, sequence diagram, class diagram) related to the answer.

Functional requirements
Sessions & storage
Create session (session_id) and store chat history in Postgres using LangChain’s Postgres chat message history integration.​

Each session has:

Document registry (doc metadata, upload status, processing status)

Vector index/namespace strategy (see “Retrieval model”)

Chat history (messages + trace ids)

Document ingestion (async)
POST /sessions/{session_id}/docs supports batch upload metadata and returns job_id immediately.​

Celery tasks:

Fetch raw file (store raw file in object storage; recommended S3-compatible).​

Parse + chunk using Docling loader integration for LangChain.​

Embed chunks with Gemini embeddings endpoint (configurable model).​

Upsert into S3 Vectors with metadata required for filtering and citations.​

Job status endpoint GET /jobs/{job_id} with pagination for job events/logs.

Retrieval model (RAG)
Similarity search via S3 Vectors QueryVectors with:

top_k configurable

metadata filters for session_id and optionally doc_id for @doc routing.​

Must store metadata as filterable when needed; S3 Vectors differentiates filterable vs non-filterable metadata and filters run alongside similarity evaluation.​

Answering + citations
The assistant response must include:

Natural-language answer

Citation objects referencing doc name + page/section + chunk id + source URI (from metadata).​

Backend returns structured response:

answer_text

citations: List[Citation]

retrieved_context: List[ChunkRef] (optional, for debug)

Mermaid diagram generation (“nano banana”)
User can request diagram explicitly (e.g., “draw a flowchart”), or backend can offer it when confidence is low / concept is procedural.

Output includes:

mermaid_code

short diagram description

Must be grounded: diagram nodes/edges should be explainable from retrieved context; if not, diagram generation should be refused or marked as “conceptual”.

Observability (Langfuse)
Every ingestion job and chat turn emits traces/spans with:

session_id, job_id, model name, token usage (if available), latency, retrieval k, filter used.​

Langfuse runs self-hosted via Docker Compose in the dev stack.​

Evaluation (Ragas)
Provide an offline evaluation runner that:

Loads a dataset of questions/ground truth/contexts/answers and calls evaluate().​

Logs results to Langfuse experiments/datasets (or stores in Postgres) for regression tracking.​

Non-functional requirements
Performance & scalability
Ingestion must be horizontally scalable via multiple Celery worker replicas; RabbitMQ is the broker.​

Use batching for vector inserts and backoff/retry on throttling (implementation detail, but required).

Reliability
Idempotent ingestion: re-running a job should not duplicate vectors (use deterministic chunk ids).

Dead-letter strategy for failed jobs (poison docs) and clear error surfaces.

Security (baseline only)
No auth, but still:

Limit upload size/types

Sanitize filenames and user-provided doc names

Prevent prompt injection from retrieved context by isolating system prompts and adding “context is untrusted” guardrails

APIs (proposed)
POST /sessions → {session_id}

POST /sessions/{session_id}/docs → {job_id, doc_ids[]}

GET /sessions/{session_id}/docs?cursor=... → paginated doc list

GET /jobs/{job_id} → job state + progress

POST /sessions/{session_id}/chat → {answer, citations, mermaid?}

POST /sessions/{session_id}/diagram → {mermaid_code, citations?}

All request/response bodies must be Pydantic models.

Open decisions
Session isolation strategy in S3 Vectors:

Separate index per session vs shared index with mandatory session_id filter (shared is simpler ops; separate is stronger isolation).​

Diagram grounding policy:

Strictly require citations for diagram claims vs allow “conceptual diagram” mode.

Evaluation cadence:

Nightly batch eval via Celery vs manual “run eval” endpoint using the same evaluate() pipeline.​






