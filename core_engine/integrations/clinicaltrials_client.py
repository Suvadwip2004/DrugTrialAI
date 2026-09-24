from __future__ import annotations
import logging
import httpx

logger  = logging.getLogger(__name__)


BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
TIMEOUT=10

DEFAULT_FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "Phase",
    "Condition",
    "InterventionName",
    "EligibilityCriteria",
    "MinimumAge",
    "MaximumAge",
    "Sex",
    "LocationCountry",
]
 
VALID_PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}
VALID_STATUSES = {
    "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", "TERMINATED",
    "WITHDRAWN", "NOT_YET_RECRUITING", "SUSPENDED", "ENROLLING_BY_INVITATION",
    "UNKNOWN",
}

async def search_trials(
        condition : str | None  = None,
        intervention : str | None  = None,
        phases : list[str] | None  = None,
        status : str  = "RECRUITING",
        page_size : int  = 10
) -> list[dict] :
    if not condition and not intervention :
        logger.warning("search_trials called with neither condition nor intervention — nothing to search")
        return []

    params : dict  = {
        "fields" : ",".join(DEFAULT_FIELDS),
        "pageSize" : page_size,
        "format" : "json"
    }

    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if phases:
        invalid  = [p for p in phases if p not in VALID_PHASES]
        if invalid :
            logger.warning("Ignoring invalid phase value(s): %s. Valid: %s", invalid, VALID_PHASES)
        valid_phases = [p for p in phases if p in VALID_PHASES]
        if valid_phases:
            phase_expr = " OR ".join(f"AREA[Phase]{p}" for p in valid_phases)
            params["filter.advanced"] = phase_expr

    if status:
        if status not in VALID_STATUSES:
            logger.warning("Invalid status '%s' — skipping status filter. Valid: %s", status, VALID_STATUSES)
        else:
            params["filter.overallStatus"] = status
        
    async with httpx.AsyncClient(timeout=TIMEOUT) as client :
        try:
            resp  = await client.get(BASE_URL,params=params)
            resp.raise_for_status()

        except httpx.HTTPStatusError as e:
            logger.error("ClinicalTrials.gov search failed (%s): %s", e.response.status_code, e.response.text)
            return []
        except httpx.HTTPError as e:
            logger.error("ClinicalTrials.gov search failed: %s", e)
            return []


    data  = resp.json()
    studies  = data.get(studies,[])

    result  = []
    for study in studies:
        protocol  = study.get("protocolSection",{})
        identification = protocol.get("")
        
    return data


if __name__ == "__main__":
    import asyncio
    import json
    logging.basicConfig(level=logging.INFO)
    async def main():
        trials = await search_trials(
            condition="Atrial Fibrillation",
            intervention="Warfarin",
            status="RECRUITING",
            page_size=5
        )
        print(trials)
        with open("clinicaltrials_client.json","w",encoding="UTF-8") as f:
            json.dump(trials,f,indent=4)

    asyncio.run(main())