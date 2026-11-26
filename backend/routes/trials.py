"""
Clinical Trials Search Endpoints.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.api_models import TrialItem
from core_engine.integrations.clinicaltrials_client import search_trials

logger = logging.getLogger("backend.routes.trials")

router = APIRouter(prefix="/trials", tags=["Clinical Trials"])


@router.get("/search", response_model=list[TrialItem])
async def query_trials(
    condition: str | None = Query(default=None, description="Condition, e.g. 'Atrial Fibrillation'"),
    intervention: str | None = Query(default=None, description="Intervention drug, e.g. 'Warfarin'"),
    phases: list[str] | None = Query(default=None, description="Trial phases (e.g. PHASE2, PHASE3)"),
    status: str = Query(default="RECRUITING", description="Recruitment status"),
    page_size: int = Query(default=10, ge=1, le=50, description="Results per page"),
) -> list[TrialItem]:
    """
    Query recruiting clinical trials directly from the official ClinicalTrials.gov API v2.
    """
    if not condition and not intervention:
        raise HTTPException(status_code=400, detail="Must provide at least 'condition' or 'intervention' parameter.")

    try:
        trials = await search_trials(
            condition=condition,
            intervention=intervention,
            phases=phases,
            status=status,
            page_size=page_size,
        )
        return [TrialItem(**t) for t in trials]
    except Exception as e:
        logger.exception("Trial search failed")
        raise HTTPException(status_code=500, detail=f"Trial search failed: {e}")
