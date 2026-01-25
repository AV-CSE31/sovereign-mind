"""
Sovereign-Mind FastAPI Application.

Enterprise-Grade Private AI Assistant with:
- Zero-Knowledge storage (encrypted chat history)
- Agentic reasoning (LangGraph)
- SOTA RAG (Hybrid search + Reranking)
- Privacy-first design (PII anonymization)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Clean up resources
    from app.services.rag_engine import _retriever

    if _retriever is not None:
        await _retriever.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Enterprise-Grade Private AI Assistant with Zero-Knowledge Storage",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    @app.get("/")
    async def root():
        return {
            "message": "Sovereign-Mind API is Online.",
            "docs": "/docs",
            "ui": "http://localhost:3000"
        }

    # CORS middleware
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if settings.debug:
        origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)

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
