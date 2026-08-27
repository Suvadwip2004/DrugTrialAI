from __future__ import annotations
import logging
import httpx
import json
import asyncio


logger  = logging.getLogger(__name__)

BASE_URL  ="https://api.fda.gov/drug/label.json"
TIMEOUT  = 10.0



async def get_drug_label(drug_name: str) -> dict | None:
    query = f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"'
    params = {"search": query, "limit": 1}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client :
        try:
            resq  = await client.get(BASE_URL,params=params)
            resq.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("No FDA label found for drug: '%s'", drug_name)
            else:
                logger.error("openFDA lookup failed for '%s': %s", drug_name, e)
            return None

    data  = resq.json()
    result  = data.get("results",[])

    return result[0] if result else None



async def get_interaction_text(drug_name: str) -> str | None:
    label  = await get_drug_label(drug_name)
    if label is None:
        return None
    interaction_section = label.get("drug_interactions")
    if not interaction_section :
        logger.warning("Label found for '%s' but no drug_interactions section present", drug_name)
        return None

    return "\n".join(interaction_section)


async def get_interaction_texts(drug_names : list[str]) -> dict[str,str|None] :
    results  : dict[str,str|None] = {}
    for name in drug_names:
        results[name] =  await get_interaction_text(name)
    return results
 




# if __name__ == "__main__":
 
#     logging.basicConfig(level=logging.INFO)
 
#     async def _main():
#         names = ["Warfarin", "Amoxicillin"]
#         texts = await get_interaction_texts(names)
#         with open("openfda.json", "w", encoding="utf-8") as file:
#             json.dump(texts, file, indent=4)
 
#         for name, text in texts.items():
#             print(f"\n=== {name} — Drug Interactions section ===")
#             if text:
#                 # print first 500 chars so terminal output stays readable
#                 print(text[:500] + ("..." if len(text) > 500 else ""))
#             else:
#                 print("(no interaction text found)")
 
#     asyncio.run(_main())
 


