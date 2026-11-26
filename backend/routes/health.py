"""
Health Check and Service Status Endpoints.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from backend.schemas.api_models import HealthResponse
from core_engine.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    """
    Check the health of the DrugTrialAI backend and dependent local services.
    """
    services: dict[str, str] = {}

    # Check Ollama connectivity
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
            services["ollama"] = "connected" if resp.status_code == 200 else f"error ({resp.status_code})"
    except Exception:
        services["ollama"] = "unreachable"

    # Check Qdrant connectivity
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/readyz")
            services["qdrant"] = "connected" if resp.status_code == 200 else f"error ({resp.status_code})"
    except Exception:
        services["qdrant"] = "unreachable"

    return HealthResponse(
        status="ok",
        version="0.1.0",
        engine="DrugTrialAI Multi-Agent Core",
        services=services,
    )
