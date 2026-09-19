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
        
)