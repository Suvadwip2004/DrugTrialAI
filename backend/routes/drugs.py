"""
Drug Information & Targeted Interaction Endpoints.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.api_models import DrugInteractionRequest, InteractionItem
from core_engine.agents.interaction_agent import analyze_all_interactions
from core_engine.integrations.openfda_client import get_interaction_text
from core_engine.integrations.rxnav_client import get_rxcui

logger = logging.getLogger("backend.routes.drugs")

router = APIRouter(prefix="/drugs", tags=["Drugs"])


@router.post("/interactions", response_model=list[InteractionItem])
async def check_drug_interactions(request: DrugInteractionRequest) -> list[InteractionItem]:
    """
    Check pairwise drug-drug interactions directly between 2 or more drugs
    with verbatim FDA label quote verification.
    """
    try:
        results = await analyze_all_interactions(request.drugs)
        return [InteractionItem(**r) for r in results]
    except Exception as e:
        logger.exception("Drug interaction check failed")
        raise HTTPException(status_code=500, detail=f"Interaction analysis failed: {e}")


@router.get("/{drug_name}/rxcui")
async def resolve_drug_rxcui(drug_name: str) -> dict:
    """
    Resolve a clinical drug name to its NLM RxCUI identifier.
    """
    rxcui = await get_rxcui(drug_name)
    if not rxcui:
        raise HTTPException(status_code=404, detail=f"No RxCUI found for drug '{drug_name}'")
    return {"drug_name": drug_name, "rxcui": rxcui}


@router.get("/{drug_name}/label")
async def get_drug_fda_label(drug_name: str) -> dict:
    """
    Fetch the official FDA package insert 'Drug Interactions' section text.
    """
    text = await get_interaction_text(drug_name)
    if not text:
        raise HTTPException(status_code=404, detail=f"No FDA drug interaction text found for '{drug_name}'")
    return {"drug_name": drug_name, "interaction_text": text}
