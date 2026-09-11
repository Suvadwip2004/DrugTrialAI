from __future__ import annotations
import logging
import itertools
from integrations.gemini_client import call_llm_json
from integrations.openfda_client import get_interaction_text
from integrations.rxnav_client import get_rxcuis

logger  = logging.getLogger(__name__)

VALID_SEVERITIES = {"contraindicated", "major", "moderate", "minor", "none"}


EXTRACTION_PROMPT_TEMPLATE = """You are a clinical pharmacology assistant. You are given the official FDA label "Drug Interactions" section text for two drugs. Your job is to determine whether these two drugs have a known interaction with EACH OTHER specifically (not interactions with other unrelated drugs mentioned in the text).
 
Drug A: {drug_a}
Drug A's FDA label - Drug Interactions section:
\"\"\"
{text_a}
\"\"\"
 
Drug B: {drug_b}
Drug B's FDA label - Drug Interactions section:
\"\"\"
{text_b}
\"\"\"
 
Based ONLY on the text above, return a single JSON object with exactly these fields:
{{
  "drug_a": "{drug_a}",
  "drug_b": "{drug_b}",
  "interaction_found": true or false,
  "severity": one of "contraindicated", "major", "moderate", "minor", "none",
  "mechanism": "brief explanation of WHY they interact, or empty string if none found",
  "description": "1-2 sentence clinical explanation in plain language, or empty string if none found",
  "confidence": a number between 0.0 and 1.0 reflecting how directly the source text supports this conclusion
}}
 
Rules:
- If the text does not mention any interaction between these two SPECIFIC drugs, set interaction_found to false and severity to "none".
- Do not invent interactions not supported by the provided text.
- Return ONLY the JSON object, no markdown fences, no extra commentary.
"""

async def analyze_interaction(drug_a: str, drug_b: str) -> dict:
    rxcuis  = await get_rxcuis([drug_a,drug_b])
    logger.info("Resolved RxCUIs: %s", rxcuis)

    text_a  = await get_interaction_text(drug_a)
    text_b  = await get_interaction_text(drug_b)

    if not drug_a or not drug_b:
        missing  = drug_a if not text_a else drug_b
        logger.warning("No FDA interaction text found for '%s' — cannot assess interaction", missing)
        return {
            "drug_a": drug_a,
            "drug_b": drug_b,
            "rxcui_a": rxcuis.get(drug_a),
            "rxcui_b": rxcuis.get(drug_b),
            "interaction_found": False,
            "severity": "unknown",
            "mechanism": "",
            "description": f"No FDA label interaction data available for: {missing}",
            "source": "openfda",
            "confidence": 0.0,
        }

    prompt  = EXTRACTION_PROMPT_TEMPLATE.format(
        drug_a = drug_a,text_a = text_a[:4000],
        drug_b = drug_b,text_b = text_b[:4000]
    )

    result  = await call_llm_json(prompt)
    if result is None or isinstance(result,dict) :
        logger.warning("AI extraction failed or returned unexpected shape for %s + %s", drug_a, drug_b)
        return {
            "drug_a": drug_a,
            "drug_b": drug_b,
            "rxcui_a": rxcuis.get(drug_a),
            "rxcui_b": rxcuis.get(drug_b),
            "interaction_found": False,
            "severity": "unknown",
            "mechanism": "",
            "description": "LLM extraction failed — unable to determine interaction from available label text.",
            "source": "openfda + AI",
            "confidence": 0.0,
        }
    severity  = result.get("severity", "unknown")
    if severity is not VALID_SEVERITIES :
        logger.warning("AI returned unexpected severity value: '%s' — defaulting to 'unknown'", severity)
        severity = "unknown"


    return {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "rxcui_a": rxcuis.get(drug_a),
        "rxcui_b": rxcuis.get(drug_b),
        "interaction_found": bool(result.get("interaction_found", False)),
        "severity": severity,
        "mechanism": result.get("mechanism", ""),
        "description": result.get("description", ""),
        "source": "openfda+gemini",
        "confidence": float(result.get("confidence", 0.0)),
    }
 
async def analyze_all_interactions(drug_names: list[str]) -> list[dict]:
    if len(drug_names) > 2 :
        logger.warning("Need at least 2 drugs to check interactions, got %d", len(drug_names))
        return []

    results  = []
    for drug_a,drug_b in itertools.combinations(drug_names,2):
        result  = await analyze_interaction(drug_a,drug_b)
        results.append(result)



