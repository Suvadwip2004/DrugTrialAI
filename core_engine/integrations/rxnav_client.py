from __future__ import annotations
import asyncio
import logging
import httpx
import json
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
    params = {"term": drug_name, "maxEntries": 1}

    async with httpx.AsyncClient(timeout  = TIMEOUT) as client :
        try:
            resp  = await client.get(url,params  = params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("RxNav lookup failed for '%s': %s", drug_name, e)
            return None
        data  = resp.json()
        candidates  = data.get("approximateGroup",{}).get("candidate",[])
        # candidates = data["approximateGroup"]["candidate"]
        
        if not candidates :
            logger.warning(f"No RxCUI match found for drug name: {drug_name}")
            return None
        return candidates[0].get("rxcui")
        

async def get_rxcuis(drug_names: list[str]) -> dict[str, str | None]:
    #     """
    # Resolve multiple drug names to RxCUIs concurrently.
    # Returns a dict mapping original drug name -> RxCUI (or None if not found).
    # """
    results  = await asyncio.gather(*(get_rxcui(name) for name in drug_names))
    return dict(zip(drug_names,results))


# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
 
#     async def _main():
#         names = ["Warfarin", "Amoxicillin"]
#         name_to_rxcui = await get_rxcuis(names)
#         print("RxCUIs:", name_to_rxcui)
 
#     asyncio.run(_main())
 
