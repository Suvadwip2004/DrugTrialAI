from __future__ import annotations
import httpx
import logging

logger  == logging.getLogger(__name__)

BASE_URL  ="https://api.fda.gov/drug/label.json"
TIMEOUT  = 10.0



async def get_drug_label(drug_name: str) -> dict | None:
    query = f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"'
    params = {"search": query, "limit": 1}
    