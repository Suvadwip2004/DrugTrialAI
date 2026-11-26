"""
DailyMed Client (NLM DailyMed REST API v2).

Fetches Structured Product Labeling (SPL) packaging metadata and label documents.
API Documentation: https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
"""

from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
TIMEOUT = 12.0


async def search_spls_by_drug_name(drug_name: str, page_size: int = 5) -> list[dict]:
    """
    Search DailyMed for Structured Product Labels (SPLs) matching a drug name.
    """
    url = f"{BASE_URL}/spls.json"
    params = {
        "drug_name": drug_name,
        "pagesize": page_size,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except httpx.HTTPError as e:
            logger.warning("DailyMed SPL lookup failed for '%s': %s", drug_name, e)
            return []


async def get_spl_details(setid: str) -> dict | None:
    """
    Fetch metadata for a specific SPL by its set ID.
    """
    url = f"{BASE_URL}/spls/{setid}.json"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data")
        except httpx.HTTPError as e:
            logger.warning("DailyMed detail lookup failed for setid '%s': %s", setid, e)
            return None
