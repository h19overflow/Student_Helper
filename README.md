# Student Helper - RAG Application

Student-focused RAG application with session-based Q&A, async document ingestion, and Mermaid diagram generation.

## Quick Start

```bash
uv sync
python -m uvicorn backend.main:app --reload
```

## Development

```bash
# Run tests
pytest tests/ -v --cov

# With test dependencies
uv sync --extra test
```
