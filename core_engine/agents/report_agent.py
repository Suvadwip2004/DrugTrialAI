from __future__ import annotations
import logging
from core_engine.integrations.llm_client import call_llm

logger  = logging.getLogger(__name__)


DISCLAIMER = (
    "> **Decision-support only.** This report summarizes retrieved FDA label text, "
    "published literature and registered trials. It is not medical advice and does "
    "not replace clinical judgment."
)


SUMMARY_PROMPT_TEMPLATE = """You are writing the executive summary of a clinical decision-support report. Summarize the facts below in 3-4 plain sentences for a clinician.
 
Rules:
- Use ONLY the facts provided. Do not add drugs, numbers, risks or recommendations that are not listed.
- Mention the overall risk level and any hard stop first.
- Return only the summary text, no headers, no markdown.
 
Facts:
{facts}
"""
 
def _clinicaltrials_url(nct_id : str | None) -> str :
    return f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else ""


