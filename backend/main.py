"""
FastAPI application entry point.

Initializes FastAPI app, registers routers, adds middleware, and configures lifespan.

Dependencies: fastapi, backend.api, backend.observability, backend.configs
System role: Application initialization and configuration
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.configs import get_settings
from backend.api import api_router
from backend.observability.middleware import CorrelationMiddleware, LangfuseMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    pass
    yield
    # Shutdown
    pass


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

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add observability middleware
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(LangfuseMiddleware)

    # Register API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
