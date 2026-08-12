import asyncio
import logging
import httpx
from __future__ import annotations

BASE_URL  = "https://rxnav.nlm.nih.gov/REST"
TIMEOUT  = 10.0
logger = logging.getLogger(__name__)






async def get_rxcui(drug_name: str) -> str | None :
    #  """Convert a drug name (e.g. 'Warfarin') into its RxNorm RxCUI code."""
    #     """
    # Resolve a drug name (e.g. 'Warfarin') to its RxNorm RxCUI code.
 
    # Uses the approximate-match endpoint so minor spelling/casing differences
    # still resolve. Returns None if no match is found.
    # """

    url  = f"{BASE_URL}/approximateTerm.json"
    


def get_drug_interactions(rxcui_list: list[str]) -> dict :
    # """Given a list of RxCUI codes, return interaction data between them."""
    ...
