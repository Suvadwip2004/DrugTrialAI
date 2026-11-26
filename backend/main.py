"""
DrugTrialAI FastAPI Application Entrypoint.

Starts the REST API server exposing endpoints for multi-agent case analysis,
direct drug interaction checks, and clinical trial matching.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import analyze, drugs, health, trials
from core_engine.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DrugTrialAI FastAPI Backend...")
    logger.info("Core Engine: LangGraph Multi-Agent System")
    logger.info("Inference: %s at %s", settings.OLLAMA_MODEL, settings.OLLAMA_HOST)
    logger.info("Vector DB: %s (Collection: %s)", settings.QDRANT_URL, settings.QDRANT_COLLECTION)
    yield
    logger.info("Shutting down DrugTrialAI FastAPI Backend...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="DrugTrialAI API",
        description=(
            "Autonomous multi-agent clinical decision-support system that detects drug-drug interactions, "
            "evaluates clinical trial eligibility, and generates structured, audit-ready reports."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include route groups
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(analyze.router, prefix="/api/v1")
    app.include_router(drugs.router, prefix="/api/v1")
    app.include_router(trials.router, prefix="/api/v1")

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "DrugTrialAI API",
            "version": "0.1.0",
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }

    return app


app = create_app()


def start():
    """Run the FastAPI application via uvicorn."""
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    start()
