"""
FastAPI application entry point.

Initializes FastAPI app, registers routers, adds middleware, and configures lifespan.

Dependencies: fastapi, backend.api, backend.observability, backend.configs
System role: Application initialization and configuration
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.configs import get_settings
from backend.api import api_router
from backend.api.routers import (
    chat_stream_router,
    diagrams_router,
    documents_router,
    health_router,
    jobs_router,
    sessions_router,
)
from backend.observability.logger import configure_logging
from backend.observability.middleware import (
    RequestLoggingMiddleware,
    CorrelationMiddleware,
    LangfuseMiddleware,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    Initializes shared resources like vector store and RAG agent.
    """
    # Startup
    configure_logging()
    logger.info("Application startup: logging configured")

    # Initialize expensive resources once at startup
    try:
        from backend.boundary.vdb.faiss_store import FAISSStore
        from backend.core.agentic_system.agent.rag_agent import RAGAgent

        logger.info("Initializing vector store and RAG agent")

        # Create vector store (reused across all requests)
        vector_store = FAISSStore(
            persist_directory=".faiss_index",
            model_id="amazon.titan-embed-text-v2:0",
            region="us-east-1",
        )
        logger.info("Vector store initialized")

        # Create RAG agent (reused across all requests)
        rag_agent = RAGAgent(
            vector_store=vector_store,
            model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            region="ap-southeast-2",
            temperature=0.0,
        )
        logger.info("RAG agent initialized")

        # Store in app state for access in request handlers
        app.state.vector_store = vector_store
        app.state.rag_agent = rag_agent

        logger.info("Application startup complete: all resources initialized")
    except Exception as e:
        logger.exception(
            "Failed to initialize application resources",
            extra={"error": str(e)},
        )
        raise

    yield

    # Shutdown
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Legal Search RAG API",
        description="Student-focused RAG application with session-based Q&A",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add observability middleware (added first = last to execute)
    app.add_middleware(LangfuseMiddleware)
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(api_router, prefix="/api/v1")

    # Register individual routers
    app.include_router(chat_stream_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(diagrams_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host="localhost",
        port=8082,
        reload=True,
    )
