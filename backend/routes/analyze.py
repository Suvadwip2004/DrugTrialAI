"""
Analysis & Multi-Agent Pipeline Endpoints.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from backend.schemas.api_models import AnalysisRequest, AnalysisResponse
from core_engine.agents.orchestrator import run_pipeline

logger = logging.getLogger("backend.routes.analyze")

router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post("", response_model=AnalysisResponse)
async def analyze_case(request: AnalysisRequest) -> AnalysisResponse:
    """
    Run the full 6-stage autonomous clinical trial and drug interaction pipeline:

    1. **check_interactions**: Resolves RxCUIs and extracts verified FDA label evidence.
    2. **assess_risk**: Computes deterministic risk scores (0-10) with patient modifiers.
    3. **find_trials**: Searches ClinicalTrials.gov and scores eligibility match criteria.
    4. **search_literature**: Hybrid RAG search over indexed PubMed abstracts.
    5. **write_report**: Assembles structured report with LLM clinical summary.
    6. **validate**: 10-point audit gate ensuring factual grounding and zero hallucinations.
    """
    try:
        patient_ctx = request.patient_context.model_dump(exclude_none=True) if request.patient_context else {}
        result = await run_pipeline(
            drugs=request.drugs,
            condition=request.condition,
            patient_context=patient_ctx,
            phases=request.phases,
        )
        return AnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Analysis pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")
