"""
Sovereign-Mind FastAPI Application.

Enterprise-Grade Private AI Assistant with:
- Zero-Knowledge storage (encrypted chat history)
- Agentic reasoning (LangGraph)
- SOTA RAG (Hybrid search + Reranking)
- Privacy-first design (PII anonymization)
"""

import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.middleware.security import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events with graceful signal handling.
    """
    # Startup
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    # Ensure data directories exist
    import os

    data_dirs = [
        settings.vault_storage_path,
        settings.audit_log_path,
        settings.chroma_persist_directory,
        "./data/temp",
    ]
    for d in data_dirs:
        os.makedirs(d, exist_ok=True)

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Start Local Inference Engine if needed
    from app.core.inference_engine import get_inference_engine

    engine = get_inference_engine()

    if "localhost" in settings.ollama_base_url or "127.0.0.1" in settings.ollama_base_url:
        engine.start()

    # Graceful shutdown handler
    def handle_shutdown(signum, frame):
        logger.info("received_shutdown_signal", signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Clean up resources
    from app.services.rag_engine import _retriever

    if _retriever is not None:
        await _retriever.close()

    if engine:
        engine.stop()

    logger.info("application_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Enterprise-Grade Private AI Assistant with Zero-Knowledge Storage",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware — explicit origin allowlisting
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    if settings.debug:
        origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )

    # Security middleware (rate limiting, headers, auth, timing)
    setup_middleware(app)

    # Include API routes
    app.include_router(router)

    @app.get("/")
    async def root():
        return {
            "message": "Sovereign-Mind API is Online.",
            "docs": "/docs",
            "ui": "http://localhost:3001",
        }

    return app


# Create the app instance
app = create_app()


# Direct run support
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
