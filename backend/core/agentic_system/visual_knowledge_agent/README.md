# Visual Knowledge Agent 📊

> Interactive concept diagram generation from AI responses via LangGraph orchestration

A sophisticated pipeline that transforms educational AI responses into interactive visual knowledge diagrams. Uses RAG document expansion, LLM-based concept curation, and Google Gemini for diagram generation.

---

## 🎯 Overview

The Visual Knowledge Agent generates interactive concept diagrams from AI responses through a four-stage pipeline orchestrated by LangGraph:

```
AI Answer → Document Expansion (RAG) → Concept Curation (LLM) → Image Generation (Gemini) → S3 Upload & Persistence → Interactive Diagram
```

**Key Capabilities:**
- 📈 Expands single AI answer into ~25 related documents via parallel RAG queries
- 🧠 Extracts 2-3 main concepts and 4-6 explorable branches using LLM
- 🎨 Generates high-quality diagrams via Google Gemini API
- 💾 Uploads images to S3 and persists metadata to database
- 🔗 Returns S3 key with structured metadata for efficient storage and retrieval
- ⚡ Async/parallel operations for performance
- 📋 Full error handling and observability

---

## 🏗️ Architecture

### Module Structure

```
backend/core/agentic_system/visual_knowledge_agent/
├── agent/
│   ├── __init__.py
│   ├── visual_knowledge_schema.py          # Data models & state schema
│   └── visual_knowledge_prompt.py          # Curation prompt template
├── graph/
│   ├── __init__.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── document_expansion_node.py      # RAG document expansion
│   │   ├── curation_node.py                # LLM concept curation
│   │   ├── image_generation_node.py        # Gemini image generation
│   │   └── s3_upload_node.py               # S3 persistence node
│   └── visual_knowledge_graph.py           # Graph orchestration
├── utilities/
│   ├── __init__.py
│   ├── document_expander.py                # RAG document expansion logic
│   └── s3_uploader.py                      # S3 image upload utility
├── __init__.py                             # Public exports
└── visual_knowledge_agent.py               # Main agent wrapper
```

### Dependency Hierarchy

```mermaid
graph TD
    A["visual_knowledge_agent.py<br/>(Main Orchestrator)"]
    A --> B["visual_knowledge_graph.py<br/>(Graph Builder)"]
    A --> C["visual_knowledge_schema.py<br/>(State & Responses)"]

    B --> D1["document_expansion_node"]
    B --> D2["curation_node"]
    B --> D3["image_generation_node"]
    B --> D4["s3_upload_node"]

    D1 --> E["document_expander.py<br/>(RAG Expansion)"]
    D2 --> F["visual_knowledge_prompt.py<br/>(LLM Prompt)"]
    D3 --> G["Google Gemini API<br/>(Image Gen)"]
    D4 --> H["s3_uploader.py<br/>(S3 Upload)"]
    D4 --> I["image_crud.py<br/>(DB Persist)"]

    E --> J["Vector Store<br/>(S3/FAISS)"]
    F --> K["Google Gemini<br/>(LLM Agent)"]
    H --> L["AWS S3<br/>(Image Storage)"]
    I --> M["ImageModel<br/>(DB Schema)"]

    style A fill:#ff6b6b,color:#fff,stroke:#c92a2a,stroke-width:2px
    style B fill:#fd7e14,color:#fff,stroke:#d9480f,stroke-width:2px
    style C fill:#fd7e14,color:#fff,stroke:#d9480f,stroke-width:2px
    style D1 fill:#20c997,color:#fff,stroke:#0b7285,stroke-width:2px
    style D2 fill:#20c997,color:#fff,stroke:#0b7285,stroke-width:2px
    style D3 fill:#20c997,color:#fff,stroke:#0b7285,stroke-width:2px
    style D4 fill:#20c997,color:#fff,stroke:#0b7285,stroke-width:2px
    style E fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style F fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style G fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style H fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style I fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style J fill:#94d82d,color:#000,stroke:#5c940d,stroke-width:2px
    style K fill:#94d82d,color:#000,stroke:#5c940d,stroke-width:2px
    style L fill:#94d82d,color:#000,stroke:#5c940d,stroke-width:2px
    style M fill:#94d82d,color:#000,stroke:#5c940d,stroke-width:2px
```

---

## 📦 Layer 1: Data Structures & Contracts

### File: [visual_knowledge_schema.py](visual_knowledge_schema.py)

Defines the complete data contract for the visual knowledge pipeline.

#### TypedDict State Schema

Used by LangGraph to track data flow through the pipeline:

```python
class VisualKnowledgeState(TypedDict, total=False):
    # Inputs
    ai_answer: str                              # User's AI response
    session_id: str | None                      # Multi-tenant context

    # Stage 1: Document Expansion
    expanded_docs: list[VectorSearchResult]     # ~25 documents

    # Stage 2: Curation
    main_concepts: list[str]                    # 2-3 core topics
    branches: list[ConceptBranch]               # 4-6 explorable topics
    image_generation_prompt: str                # Detailed Gemini instructions

    # Stage 3: Image Generation
    image_base64: str                           # PNG diagram (base64)
    mime_type: str                              # "image/png"

    # Error tracking
    error: str | None                           # Pipeline errors
```

#### Response Models

**ConceptBranch** - Explorable topic in the diagram:
```python
class ConceptBranch(BaseModel):
    id: str              # Unique ID (e.g., "branch_1")
    label: str           # Human-readable (e.g., "Activation Functions")
    description: str     # 10-20 words explaining the topic
```

**VisualKnowledgeResponse** - Complete pipeline output:
```python
class VisualKnowledgeResponse(BaseModel):
    image_base64: str                   # Base64 PNG for inline display
    mime_type: str = "image/png"        # Image MIME type
    main_concepts: list[str]            # ["Concept 1", "Concept 2"]
    branches: list[ConceptBranch]       # Explorable subtopics
    image_generation_prompt: str        # Gemini prompt (transparency)
```

---

## 🎤 Layer 2: Prompt Templates

### File: [visual_knowledge_prompt.py](visual_knowledge_prompt.py)

Instructs the curation agent to extract knowledge and create image prompts.

#### Curation Prompt Strategy

The system prompt guides the curation agent to:

1. **Extract Main Concepts** (2-3)
   - Broad, unifying topics
   - Each 1-3 words
   - Example: `["Machine Learning", "Neural Networks"]`

2. **Identify Branches** (4-6)
   - Specific explorable sub-topics
   - Each with id, label, and 10-20 word description
   - Example: `{"id": "branch_1", "label": "Backpropagation", "description": "How neural networks learn through gradient-based optimization"}`

3. **Generate Image Prompt**
   - Detailed instructions for Gemini
   - Specifies: structure, content, style, relationships, colors
   - Example: `"Create a mind map with 'ML' at center, branches for supervised/unsupervised learning..."`

#### Contract Output

```python
class CurationResult(BaseModel):
    main_concepts: list[str]                # Extracted core topics
    branches: list[ConceptBranch]          # Explorable concepts
    image_generation_prompt: str            # Gemini instruction
```

---

## 🔍 Layer 3: Document Expansion

### File: [document_expander.py](document_expander.py)

Non-agentic document retrieval that expands a single AI answer into ~25 related documents.

#### Expansion Pipeline

```mermaid
graph LR
    A["AI Answer<br/>(1 doc)"]
    -->|"similarity_search<br/>k=5"| B["Initial Docs<br/>(5 docs)"]

    B -->|"For each doc:<br/>query first 200 chars<br/>parallel asyncio.gather"| C["Expansion Results<br/>(25 docs)"]

    C -->|"Deduplicate by<br/>source_uri"| D["Unique Docs<br/>~25 docs"]

    style A fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style B fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style C fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style D fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
```

#### Function Signature

```python
async def expand_documents(
    vector_store: BaseVectorsStore,
    ai_answer: str,
    session_id: str | None = None,
) -> list[VectorSearchResult]:
    """
    Expands AI answer into ~25 related documents through recursive RAG queries.

    Returns:
        VectorSearchResult: [
            {
                chunk_id: str,
                content: str,
                metadata: {
                    session_id: str,
                    doc_id: str,
                    chunk_id: str,
                    page: int | None,
                    section: str | None,
                    source_uri: str,
                },
                similarity_score: float (0.0-1.0),
            }
        ]
    """
```

#### Key Implementation Details

- **Async-first**: Uses `run_in_threadpool` wrapper for vector store (sync API)
- **Parallel expansion**: `asyncio.gather()` for concurrent queries
- **Deduplication**: By `source_uri` to avoid duplicate content
- **Error handling**: Logs and re-raises exceptions per CLAUDE.md

---

## 🔗 Layer 4: Graph Nodes

### File: [graph_nodes.py](graph_nodes.py)

Three stateful node functions that operate on `VisualKnowledgeState`.

#### Node 1: Document Expansion

```python
async def document_expansion_node(
    state: VisualKnowledgeState,
    vector_store: BaseVectorsStore,
) -> dict:
    """
    Expands documents from AI answer via RAG.

    Input:  state["ai_answer"]
    Output: state["expanded_docs"] = list[VectorSearchResult]
    """
```

**Input Contract:**
- `state["ai_answer"]`: str (the AI response)
- `state["session_id"]`: str | None (optional context)

**Output Contract:**
- Updates state with `expanded_docs`: list[VectorSearchResult]
- On error: returns `{"error": str}`

#### Node 2: Curation

```python
def curation_node(
    state: VisualKnowledgeState,
    curation_agent: RAGAgent,  # LangChain agent with create_agent
) -> dict:
    """
    Extracts concepts and creates image generation prompt.

    Input:  state["expanded_docs"]
    Output: state["main_concepts"], state["branches"], state["image_generation_prompt"]
    """
```

**Input Contract:**
- `state["expanded_docs"]`: list[VectorSearchResult]
- Curation agent initialized with `response_format=ToolStrategy(CurationResult)`

**Output Contract:**
- `main_concepts`: list[str]
- `branches`: list[ConceptBranch]
- `image_generation_prompt`: str
- On error: returns `{"error": str}`

#### Node 3: Image Generation

```python
def image_generation_node(
    state: VisualKnowledgeState,
    google_client: genai.Client,
) -> dict:
    """
    Generates diagram via Google Gemini.

    Input:  state["image_generation_prompt"]
    Output: state["image_base64"], state["mime_type"]
    """
```

**Input Contract:**
- `state["image_generation_prompt"]`: str
- Google Gemini client (google.genai.Client)

**Output Contract:**
- `image_base64`: str (base64-encoded PNG)
- `mime_type`: str (always "image/png")
- On error: returns `{"error": str}`

#### Node 4: S3 Upload & Persistence

```python
async def s3_upload_node(
    state: VisualKnowledgeState,
    s3_uploader: S3ImageUploader,
    db_session: AsyncSession,
) -> dict:
    """
    Upload image to S3 and persist metadata to database.

    Input:  state[\"image_base64\"], state[\"mime_type\"], curation data
    Output: state[\"s3_key\"], state[\"image_id\"], removes state[\"image_base64\"]
    """
```

**Input Contract:**
- `state["image_base64"]`: str (base64-encoded image from previous node)
- `state["mime_type"]`: str (image MIME type)
- `state["main_concepts"]`, `state["branches"]`, `state["image_generation_prompt"]`: Curation metadata
- S3ImageUploader service for image persistence
- AsyncSession for database operations

**Output Contract:**
- `s3_key`: str (S3 object location, e.g., "sessions/{session_id}/images/{image_id}.png")
- `image_id`: str (UUID of persisted database record)
- `image_base64`: None (cleared from state for memory efficiency)
- `mime_type`: str (detected MIME type)
- On error: returns `{"error": str}`

#### Node Execution Model

```mermaid
graph TD
    A["Input State<br/>VisualKnowledgeState"]
    -->|"Process"| B["Node Function"]
    -->|"Update State"| C["Output Dict<br/>{key: value}"]
    -->|"Merge"| D["Updated State<br/>VisualKnowledgeState"]
    -->|"Pass to<br/>Next Node"| E["Next Node"]

    B -->|"Exception"| F["Return error dict<br/>{error: str}"]
    F --> D

    style A fill:#a8e6cf,color:#000,stroke:#2f5233,stroke-width:2px
    style B fill:#56ab91,color:#fff,stroke:#0b4332,stroke-width:2px
    style C fill:#38ada9,color:#fff,stroke:#023e8a,stroke-width:2px
    style D fill:#006d77,color:#fff,stroke:#00364d,stroke-width:2px
    style E fill:#003d5c,color:#fff,stroke:#001233,stroke-width:2px
    style F fill:#e76f51,color:#fff,stroke:#d62828,stroke-width:2px
```

---

## 🕸️ Layer 5: Graph Orchestration

### File: [visual_knowledge_graph.py](visual_knowledge_graph.py)

Builds and compiles the LangGraph that orchestrates the four nodes.

#### Graph Builder

```python
def create_visual_knowledge_graph(
    vector_store: BaseVectorsStore,
    curation_agent: RAGAgent,
    google_client: genai.Client,
    s3_uploader: S3ImageUploader,
    db_session: AsyncSession,
) -> CompiledGraph:
    """
    Creates LangGraph for visual knowledge pipeline.

    Structure:
        Entry: document_expansion
              ↓
        document_expansion → curation
              ↓
        curation → image_generation
              ↓
        image_generation → s3_upload
              ↓
        s3_upload → END
    """
```

#### Graph Flow Diagram

```mermaid
graph LR
    A["START:<br/>Input State"]
    -->|"ai_answer<br/>session_id"| B["document_expansion<br/>(async node)"]

    B -->|"expanded_docs"| C["curation<br/>(sync node)"]

    C -->|"main_concepts<br/>branches<br/>image_prompt"| D["image_generation<br/>(sync node)"]

    D -->|"image_base64<br/>mime_type"| E["s3_upload<br/>(async node)"]

    E -->|"s3_key<br/>image_id"| F["END:<br/>Complete State"]

    style A fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style B fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style C fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style D fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style E fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style F fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
```

#### Dependency Injection Pattern

Dependencies are bound to nodes via closures:

```python
graph.add_node(
    "document_expansion",
    lambda state: document_expansion_node(state, vector_store),  # Inject vector_store
)
graph.add_node(
    "curation",
    lambda state: curation_node(state, curation_agent),  # Inject agent
)
graph.add_node(
    "image_generation",
    lambda state: image_generation_node(state, google_client),  # Inject client
)
graph.add_node(
    "s3_upload",
    lambda state: s3_upload_node(state, s3_uploader, db_session),  # Inject uploader & session
)
```

---

## 📦 Layer 5.5: S3 Image Upload Utility

### File: [utilities/s3_uploader.py](utilities/s3_uploader.py)

Handles base64 image encoding, MIME type detection, and S3 persistence with proper metadata.

#### Class Definition

```python
class S3ImageUploader:
    """Uploads generated images to S3 bucket with metadata."""

    def __init__(self, s3_client: boto3.client, bucket_name: str) -> None:
        """Initialize with boto3 S3 client and bucket name."""

    async def upload_image(
        self,
        image_base64: str,
        session_id: UUID,
    ) -> tuple[str, str]:
        """
        Upload base64 image to S3 with automatic MIME type detection.

        Returns:
            Tuple of (s3_key, mime_type)
        """
```

#### Key Features

- **MIME Type Detection**: Analyzes magic bytes in base64 data to detect PNG, JPEG, GIF, WebP
- **Async Upload**: Uses `asyncio.to_thread()` to wrap sync boto3 calls
- **S3 Key Structure**: `sessions/{session_id}/images/{image_id}.{extension}`
- **Metadata Storage**: Stores session_id and image_id in S3 object metadata
- **Error Handling**: Validates inputs and raises ValueError on invalid data

#### Upload Contract

**Input:**
- `image_base64`: str (base64-encoded image from previous node)
- `session_id`: UUID (for S3 path structure)

**Output:**
- `s3_key`: str (S3 object key for retrieval)
- `mime_type`: str (detected MIME type for correct rendering)

**Raises:**
- `ValueError`: If image_base64 is empty or session_id missing
- `Exception`: If S3 upload fails

---

## 📊 Layer 5.75: Database Models & CRUD

### File: [backend/boundary/db/models/image_model.py](../../../boundary/db/models/image_model.py)

SQLAlchemy ORM model for persisting image metadata and curation data.

#### Model Definition

```python
class ImageModel(Base, UUIDMixin, TimestampMixin):
    """
    ORM model for visual knowledge diagram images.

    Attributes:
        id: UUID primary key
        session_id: Foreign key to SessionModel (CASCADE delete)
        s3_key: S3 object location
        mime_type: Image MIME type
        message_index: Optional chat message position
        main_concepts: JSON array of concept strings
        branches: JSON array of branch objects
        image_generation_prompt: Full Gemini prompt for audit
    """
```

#### Database Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `session_id` | UUID | Foreign key to sessions (CASCADE) |
| `s3_key` | String(1024) | S3 object location |
| `mime_type` | String(50) | Image MIME type (default: image/png) |
| `message_index` | Integer | Optional chat message position (0-indexed) |
| `main_concepts` | JSON | Array of 2-3 concept strings |
| `branches` | JSON | Array of branch objects with id, label, description |
| `image_generation_prompt` | String(4096) | Full Gemini prompt for regeneration |
| `created_at` | DateTime | Image generation timestamp (UTC) |
| `updated_at` | DateTime | Last modification timestamp (UTC) |

### File: [backend/boundary/db/CRUD/image_crud.py](../../../boundary/db/CRUD/image_crud.py)

CRUD operations for ImageModel with session filtering and message linking.

#### CRUD Interface

```python
class ImageCRUD(BaseCRUD[ImageModel]):
    """CRUD operations for ImageModel."""

    async def get_by_session_id(
        self,
        session: AsyncSession,
        session_id: UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[ImageModel]:
        """Retrieve images for session (newest first)."""

    async def get_by_message_index(
        self,
        session: AsyncSession,
        session_id: UUID,
        message_index: int,
    ) -> ImageModel | None:
        """Retrieve image linked to specific chat message."""

    async def get_latest_for_session(
        self,
        session: AsyncSession,
        session_id: UUID,
    ) -> ImageModel | None:
        """Retrieve most recently created image for session."""

    async def create_from_generation(
        self,
        session: AsyncSession,
        session_id: UUID,
        s3_key: str,
        mime_type: str,
        main_concepts: list[str],
        branches: list[dict],
        image_generation_prompt: str,
        message_index: int | None = None,
    ) -> ImageModel:
        """Create image record from generation output."""
```

#### Key Methods

- **get_by_session_id**: Retrieve all images for a session, ordered by creation (newest first)
- **get_by_message_index**: Link images to specific chat messages for retrieval
- **get_latest_for_session**: Quick access to most recent diagram
- **create_from_generation**: Specialized factory method to persist complete generation data

---

## 🤖 Layer 6: Agent Wrapper

### File: [visual_knowledge_agent.py](visual_knowledge_agent.py)

Main orchestrator class that wraps the LangGraph and provides a clean async interface.

#### Class Definition

```python
class VisualKnowledgeAgent:
    """Orchestrates document expansion → curation → image generation via LangGraph."""

    def __init__(
        self,
        google_api_key: str,
        vector_store: BaseVectorsStore,
        model_id: str = "gemini-3-flash-preview",
        temperature: float = 0.0,
    ) -> None:
        """Initialize with Google Gemini and vector store."""
        # Initializes:
        # - Google Gemini client (google.genai.Client)
        # - Curation agent (create_agent + ToolStrategy)
        # - LangGraph pipeline

    async def ainvoke(
        self,
        ai_answer: str,
        session_id: str | None = None,
    ) -> VisualKnowledgeResponse:
        """
        Generate visual knowledge diagram.

        Returns: VisualKnowledgeResponse with image + metadata
        Raises: RuntimeError on pipeline failure
        """
```

#### Initialization Flow

```mermaid
graph TD
    A["VisualKnowledgeAgent<br/>Constructor"]

    A -->|"os.getenv<br/>GOOGLE_API_KEY"| B["Initialize<br/>Google Client<br/>genai.Client"]

    A -->|"create_agent +<br/>ToolStrategy"| C["Initialize<br/>Curation Agent<br/>RAGAgent"]

    A -->|"Inject dependencies<br/>vector_store, agent, client"| D["Create<br/>LangGraph<br/>create_visual_knowledge_graph"]

    D --> E["Compiled Graph<br/>Ready for ainvoke"]

    style A fill:#ff6b6b,color:#fff,stroke:#c92a2a,stroke-width:2px
    style B fill:#fd7e14,color:#fff,stroke:#d9480f,stroke-width:2px
    style C fill:#fd7e14,color:#fff,stroke:#d9480f,stroke-width:2px
    style D fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style E fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
```

#### Invocation Contract

```python
# Input
await agent.ainvoke(
    ai_answer="Machine learning is...",
    session_id="sess-123"
)

# Output
VisualKnowledgeResponse(
    image_base64="iVBORw0KGgoAAAANSUhEUgA...",
    mime_type="image/png",
    main_concepts=["Machine Learning", "Neural Networks"],
    branches=[
        ConceptBranch(
            id="branch_1",
            label="Supervised Learning",
            description="Learning from labeled examples..."
        ),
        ...
    ],
    image_generation_prompt="Create a modern mind map with..."
)

# Error Handling
RuntimeError: "Visual knowledge generation failed: {error_msg}"
ValueError: "ai_answer cannot be empty"
```

---

## 🔧 Layer 7: Service Integration

### File: [backend/application/services/visual_knowledge_service.py](../../../application/services/visual_knowledge_service.py)

Service layer that orchestrates between API and agent.

```python
class VisualKnowledgeService:
    """Orchestrates visual knowledge generation."""

    def __init__(self, visual_knowledge_agent: VisualKnowledgeAgent):
        self._agent = visual_knowledge_agent

    async def generate(
        self,
        session_id: str,
        ai_answer: str,
    ) -> VisualKnowledgeResponseModel:
        """
        Generate visual knowledge diagram.

        Returns: VisualKnowledgeResponseModel (API model)
        Raises: ValueError | RuntimeError
        """
        # 1. Log generation start
        # 2. Call agent.ainvoke(ai_answer, session_id)
        # 3. Convert to VisualKnowledgeResponseModel
        # 4. Log success
        # 5. Error handling with CLAUDE.md format logging
```

---

## 🌐 Layer 8: API Contracts

### File: [backend/models/visual_knowledge.py](../../../models/visual_knowledge.py)

Pydantic DTOs for HTTP API contracts.

#### Request Model

```python
class VisualKnowledgeRequest(BaseModel):
    ai_answer: str = Field(
        min_length=1,
        description="The assistant response to visualize as a diagram"
    )
```

#### Response Model

```python
class VisualKnowledgeResponseModel(BaseModel):
    image_base64: str                   # Base64 PNG
    mime_type: str = "image/png"        # Always image/png
    main_concepts: list[str]            # ["Concept 1", ...]
    branches: list[ConceptBranchResponse]  # Explorable topics
    image_generation_prompt: str        # Gemini prompt (transparency)
```

### API Endpoint

**POST** `/sessions/{session_id}/visual-knowledge`

```python
@router.post(
    "/{session_id}/visual-knowledge",
    response_model=VisualKnowledgeResponseModel,
    status_code=200,
)
async def generate_visual_knowledge(
    session_id: str,
    request: VisualKnowledgeRequest,
    visual_knowledge_service = Depends(get_visual_knowledge_service),
) -> VisualKnowledgeResponseModel:
    """
    Generate visual knowledge diagram for assistant message.

    Request:  {"ai_answer": "Your AI response..."}
    Response: {"image_base64": "...", "mime_type": "...", ...}
    Errors:   400 (ValueError) | 500 (Exception)
    """
```

---

## 📊 Complete Data Flow

### End-to-End Pipeline

```mermaid
graph LR
    A["User clicks<br/>Visualize"]
    -->|"POST /sessions/id/visual-knowledge<br/>{ai_answer: str}"| B["API Endpoint"]

    B -->|"visual_knowledge_service.generate"| C["VisualKnowledgeService"]

    C -->|"agent.ainvoke"| D["VisualKnowledgeAgent"]

    D -->|"graph.ainvoke"| E["LangGraph"]

    E -->|"Node 1"| F["document_expansion_node"]
    F -->|"expand_documents"| G["Vector Store<br/>S3/FAISS"]
    G -->|"~25 docs"| H["Updated State"]

    H -->|"Node 2"| I["curation_node"]
    I -->|"curation_agent.invoke"| J["Google Gemini<br/>LLM"]
    J -->|"CurationResult"| K["Updated State"]

    K -->|"Node 3"| L["image_generation_node"]
    L -->|"google_client.generate_content"| M["Google Gemini<br/>Image Gen"]
    M -->|"PNG bytes"| N["Updated State"]

    N -->|"Node 4"| O["s3_upload_node"]
    O -->|"upload_image + persist"| P["S3 + Database"]
    P -->|"s3_key, image_id"| Q["Updated State"]

    Q -->|"VisualKnowledgeResponse"| R["Agent"]
    R -->|"VisualKnowledgeResponseModel"| S["Service"]
    S -->|"JSON Response"| T["API Endpoint"]

    T -->|"200 OK<br/>{s3_key, image_id, ...}"| U["Frontend"]
    U -->|"Fetch from S3<br/>Show branches"| V["User sees diagram"]

    style A fill:#a8e6cf,color:#000,stroke:#2f5233,stroke-width:2px
    style B fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style C fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style D fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style E fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style F fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style G fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style H fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style I fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style J fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style K fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style L fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style M fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style N fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style O fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style P fill:#94d82d,color:#000,stroke:#5c940d,stroke-width:2px
    style Q fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style R fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
    style S fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
    style T fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
    style U fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
    style V fill:#2f5233,color:#fff,stroke:#0b2618,stroke-width:2px
```

---

## 🚀 Usage

### Dependency Injection

```python
# backend/api/deps/dependencies.py
def get_visual_knowledge_service(db_session: AsyncSession = Depends(get_db_session)):
    """Factory function for dependency injection."""
    import os
    import boto3
    from backend.core.agentic_system.visual_knowledge_agent import VisualKnowledgeAgent
    from backend.core.agentic_system.visual_knowledge_agent.utilities.s3_uploader import S3ImageUploader
    from backend.application.services.visual_knowledge_service import VisualKnowledgeService
    from backend.boundary.vdb.vector_store_factory import get_vector_store

    google_api_key = os.getenv("GOOGLE_API_KEY")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_bucket = os.getenv("S3_BUCKET_NAME", "student-helper-diagrams")

    vector_store = get_vector_store()

    # Initialize S3 client and uploader
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    s3_uploader = S3ImageUploader(s3_client, s3_bucket)

    agent = VisualKnowledgeAgent(
        google_api_key=google_api_key,
        vector_store=vector_store,
        s3_uploader=s3_uploader,
        db_session=db_session,
        model_id="gemini-3-flash-preview",
        temperature=0.0,
    )

    return VisualKnowledgeService(visual_knowledge_agent=agent)
```

### API Usage

```bash
# Request
curl -X POST http://localhost:8000/sessions/sess-123/visual-knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "ai_answer": "Machine learning is a subset of artificial intelligence..."
  }'

# Response (200 OK)
{
  "s3_key": "sessions/550e8400-e29b-41d4-a716-446655440000/images/7d8c5f2a-1b3e-4f9d-8a5b-2c1e9d7f4a6b.png",
  "image_id": "7d8c5f2a-1b3e-4f9d-8a5b-2c1e9d7f4a6b",
  "mime_type": "image/png",
  "main_concepts": [
    "Machine Learning",
    "Artificial Intelligence"
  ],
  "branches": [
    {
      "id": "branch_1",
      "label": "Supervised Learning",
      "description": "Learning from labeled examples with defined outcomes"
    },
    {
      "id": "branch_2",
      "label": "Unsupervised Learning",
      "description": "Finding patterns in unlabeled data without predefined outcomes"
    },
    ...
  ],
  "image_generation_prompt": "Create a modern mind map with 'Machine Learning' at center..."
}
```

---

## 📋 Contract Summary

### State Transitions

```mermaid
stateDiagram-v2
    [*] --> Initial: VisualKnowledgeState
    Initial: ai_answer, session_id

    Initial --> Expanded: Document Expansion
    Expanded: expanded_docs (~25)

    Expanded --> Curated: Curation
    Curated: main_concepts, branches, image_prompt

    Curated --> Generated: Image Generation
    Generated: image_base64, mime_type

    Generated --> Persisted: S3 Upload & DB Persist
    Persisted: s3_key, image_id

    Persisted --> [*]: VisualKnowledgeResponse

    note right of Initial
        Input from user request
    end note

    note right of Expanded
        RAG expansion via vector store
    end note

    note right of Curated
        LLM concept extraction
    end note

    note right of Generated
        Gemini diagram creation
    end note

    note right of Persisted
        S3 upload + database persistence
    end note

    style Initial fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style Expanded fill:#4dabf7,color:#fff,stroke:#1864ab,stroke-width:2px
    style Curated fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style Generated fill:#339af0,color:#fff,stroke:#1155cc,stroke-width:2px
    style Persisted fill:#1971c2,color:#fff,stroke:#0c4a6e,stroke-width:2px
```

### Error Handling Strategy

```mermaid
graph TD
    A["Node Execution"]

    A -->|"Exception"| B["Log Error<br/>{__name__}:{func} - {type}: {msg}"]
    B --> C{"Node Type"}

    C -->|"doc_expansion"| D["Return {error: str}<br/>Continue to next node"]
    C -->|"curation"| D
    C -->|"image_generation"| D

    D --> E["Agent checks<br/>final_state[error]"]

    E -->|"error present"| F["Raise RuntimeError<br/>with details"]
    E -->|"no error"| G["Return<br/>VisualKnowledgeResponse"]

    style A fill:#74c0fc,color:#000,stroke:#1971c2,stroke-width:2px
    style B fill:#ff6b6b,color:#fff,stroke:#c92a2a,stroke-width:2px
    style C fill:#fd7e14,color:#fff,stroke:#d9480f,stroke-width:2px
    style D fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style E fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
    style F fill:#ff6b6b,color:#fff,stroke:#c92a2a,stroke-width:2px
    style G fill:#51cf66,color:#000,stroke:#2f9e44,stroke-width:2px
```

---

## 🔒 Key Assumptions & Contracts

| Component | Assumption | Contract |
|-----------|-----------|----------|
| **Vector Store** | Synchronous API | `similarity_search(query, k) → list[VectorSearchResult]` |
| **Google Gemini** | Available API key | `genai.Client(api_key=str)` + `models.generate_content()` |
| **LLM Agent** | Structured output | `create_agent + ToolStrategy(CurationResult)` returns `{"structured_response": CurationResult}` |
| **Document Content** | Tokenizable | First 200 chars used as expansion query |
| **Image Response** | Contains PNG | `response.candidates[0].content.parts[*].inline_data.data` is bytes |

---

## 📝 Logging Format

All functions follow CLAUDE.md logging standards:

```python
logger.error(f"{__name__}:function_name - {type(e).__name__}: {e}")
```

**Examples:**
```
backend.core.agentic_system.visual_knowledge_agent.document_expander:expand_documents - ValueError: Query cannot be empty
backend.core.agentic_system.visual_knowledge_agent.graph_nodes:curation_node - RuntimeError: Curation agent returned invalid response
```

---

## 🧪 Testing Strategy

**Unit Test Coverage:**
- [ ] Schema validation (Pydantic models)
- [ ] Document expansion with mock vector store
- [ ] Curation node with mocked LLM responses
- [ ] Image generation with mocked Gemini API
- [ ] S3ImageUploader with mock boto3 client
- [ ] s3_upload_node with mocked uploader and db session
- [ ] Graph state transitions
- [ ] Error handling and logging
- [ ] MIME type detection from base64 data

**Integration Test Coverage:**
- [ ] Full pipeline with test data
- [ ] Service layer integration
- [ ] API endpoint (mock dependencies)
- [ ] S3 upload with real boto3 client (optional)
- [ ] Database persistence with test database

---

## 📚 File Reference Guide

| File | Purpose | Key Exports |
|------|---------|-------------|
| [agent/visual_knowledge_schema.py](agent/visual_knowledge_schema.py) | Data models & TypedDict state | `VisualKnowledgeState`, `CurationResult`, `VisualKnowledgeResponse` |
| [agent/visual_knowledge_prompt.py](agent/visual_knowledge_prompt.py) | LLM instructions | `VISUAL_KNOWLEDGE_PROMPT`, `get_visual_knowledge_prompt()` |
| [utilities/document_expander.py](utilities/document_expander.py) | RAG document expansion | `expand_documents(...)` |
| [utilities/s3_uploader.py](utilities/s3_uploader.py) | S3 image upload utility | `S3ImageUploader` |
| [graph/nodes/document_expansion_node.py](graph/nodes/document_expansion_node.py) | Document expansion node | `document_expansion_node` |
| [graph/nodes/curation_node.py](graph/nodes/curation_node.py) | Curation node | `curation_node` |
| [graph/nodes/image_generation_node.py](graph/nodes/image_generation_node.py) | Image generation node | `image_generation_node` |
| [graph/nodes/s3_upload_node.py](graph/nodes/s3_upload_node.py) | S3 upload & persistence node | `s3_upload_node` |
| [graph/visual_knowledge_graph.py](graph/visual_knowledge_graph.py) | LangGraph builder | `create_visual_knowledge_graph(...)` |
| [visual_knowledge_agent.py](visual_knowledge_agent.py) | Main orchestrator | `VisualKnowledgeAgent` |
| [__init__.py](__init__.py) | Public module interface | All public exports |
| [backend/boundary/db/models/image_model.py](../../../boundary/db/models/image_model.py) | Image ORM model | `ImageModel` |
| [backend/boundary/db/CRUD/image_crud.py](../../../boundary/db/CRUD/image_crud.py) | Image CRUD operations | `ImageCRUD`, `image_crud` |

---

## 🔗 Related Files

**Service Layer:**
- [backend/application/services/visual_knowledge_service.py](../../../application/services/visual_knowledge_service.py) - Orchestrates agent

**API Integration:**
- [backend/api/routers/sessions.py](../../../api/routers/sessions.py) - HTTP endpoint
- [backend/api/deps/dependencies.py](../../../api/deps/dependencies.py) - Dependency injection

**Data Models:**
- [backend/models/visual_knowledge.py](../../../models/visual_knowledge.py) - API DTOs

---

## 🎓 Design Principles

1. **Separation of Concerns**: Schemas, prompts, expansion, nodes, graph, agent are isolated
2. **Dependency Injection**: Dependencies injected via closures to nodes
3. **Async-First**: Parallel RAG queries via `asyncio.gather()`
4. **Error Propagation**: Errors tracked in state, checked at agent level
5. **Type Safety**: Full type hints throughout
6. **Observability**: Structured logging at all levels

---

## 📄 License & Attribution

Part of the Student Helper RAG application. Built with:
- **LangGraph**: Stateful graph orchestration
- **LangChain**: Agent framework with structured output
- **Google Gemini**: LLM and image generation
- **Google Gemini API**: Image generation
- **FastAPI**: HTTP API framework
- **AWS S3**: Image storage
- **SQLAlchemy**: Database ORM and persistence
- **Boto3**: AWS S3 integration

---

**Last Updated:** 2025-12-20
**Module Version:** 1.1.0
**Changes:** Added S3 image persistence layer (Layer 5.5), database models (Layer 5.75), and s3_upload_node (Node 4)
