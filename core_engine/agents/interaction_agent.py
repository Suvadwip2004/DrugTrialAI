# from __future__ import annotations
# import logging
# import itertools
# from core_engine.integrations.llm_client import call_llm_json
# from core_engine.integrations.openfda_client import get_interaction_text
# from core_engine.integrations.rxnav_client import get_rxcuis

# logger  = logging.getLogger(__name__)

# VALID_SEVERITIES = {"contraindicated", "major", "moderate", "minor", "none"}


# EXTRACTION_PROMPT_TEMPLATE = """You are a clinical pharmacology assistant. You are given the official FDA label "Drug Interactions" section text for two drugs. Your job is to determine whether these two drugs have a known interaction with EACH OTHER specifically (not interactions with other unrelated drugs mentioned in the text).
 
# Drug A: {drug_a}
# Drug A's FDA label - Drug Interactions section:
# \"\"\"
# {text_a}
# \"\"\"
 
# Drug B: {drug_b}
# Drug B's FDA label - Drug Interactions section:
# \"\"\"
# {text_b}
# \"\"\"
 
# Based ONLY on the text above, return a single JSON object with exactly these fields:
# {{
#   "drug_a": "{drug_a}",
#   "drug_b": "{drug_b}",
#   "interaction_found": true or false,
#   "severity": one of "contraindicated", "major", "moderate", "minor", "none",
#   "mechanism": "brief explanation of WHY they interact, or empty string if none found",
#   "description": "1-2 sentence clinical explanation in plain language, or empty string if none found",
#   "confidence": a number between 0.0 and 1.0 reflecting how directly the source text supports this conclusion
# }}
 
# Rules:
# - If the text does not mention any interaction between these two SPECIFIC drugs, set interaction_found to false and severity to "none".
# - Do not invent interactions not supported by the provided text.
# - Return ONLY the JSON object, no markdown fences, no extra commentary.
# """

# async def analyze_interaction(drug_a: str, drug_b: str) -> dict:
#     rxcuis  = await get_rxcuis([drug_a,drug_b])
#     logger.info("Resolved RxCUIs: %s", rxcuis)

#     text_a  = await get_interaction_text(drug_a)
#     text_b  = await get_interaction_text(drug_b)

#     if not text_a or not text_b:
#         missing  = drug_a if not text_a else drug_b
#         logger.warning("No FDA interaction text found for '%s' — cannot assess interaction", missing)
#         return {
#             "drug_a": drug_a,
#             "drug_b": drug_b,
#             "rxcui_a": rxcuis.get(drug_a),
#             "rxcui_b": rxcuis.get(drug_b),
#             "interaction_found": False,
#             "severity": "unknown",
#             "mechanism": "",
#             "description": f"No FDA label interaction data available for: {missing}",
#             "source": "openfda",
#             "confidence": 0.0,
#         }

#     prompt  = EXTRACTION_PROMPT_TEMPLATE.format(
#         drug_a = drug_a,text_a = text_a[:4000],
#         drug_b = drug_b,text_b = text_b[:4000]
#     )

#     result  = await call_llm_json(prompt)
#     if result is None or not isinstance(result,dict) :
#         logger.warning("AI extraction failed or returned unexpected shape for %s + %s", drug_a, drug_b)
#         return {
#             "drug_a": drug_a,
#             "drug_b": drug_b,
#             "rxcui_a": rxcuis.get(drug_a),
#             "rxcui_b": rxcuis.get(drug_b),
#             "interaction_found": False,
#             "severity": "unknown",
#             "mechanism": "",
#             "description": "LLM extraction failed — unable to determine interaction from available label text.",
#             "source": "openfda + AI",
#             "confidence": 0.0,
#         }
#     severity  = result.get("severity", "unknown")
#     if severity not in VALID_SEVERITIES :
#         logger.warning("AI returned unexpected severity value: '%s' — defaulting to 'unknown'", severity)
#         severity = "unknown"


#     return {
#         "drug_a": drug_a,
#         "drug_b": drug_b,
#         "rxcui_a": rxcuis.get(drug_a),
#         "rxcui_b": rxcuis.get(drug_b),
#         "interaction_found": bool(result.get("interaction_found", False)),
#         "severity": severity,
#         "mechanism": result.get("mechanism", ""),
#         "description": result.get("description", ""),
#         "source": "openfda + Drug AI ",
#         "confidence": float(result.get("confidence", 0.0)),
#     }
 
# async def analyze_all_interactions(drug_names: list[str]) -> list[dict]:
#     if len(drug_names) < 2 :
#         logger.warning("Need at least 2 drugs to check interactions, got %d", len(drug_names))
#         return []

#     results  = []
#     for drug_a,drug_b in itertools.combinations(drug_names,2):
#         result  = await analyze_interaction(drug_a,drug_b)
#         results.append(result)

#     return results

# def _as_bool(value) -> bool:
#     if isinstance(value, str):
#         return value.strip().lower() in {"true", "yes", "1"}
#     return bool(value)


# def _normalize_extraction(result: dict) -> dict:
#     found = _as_bool(result.get("interaction_found", False))
#     severity = str(result.get("severity", "unknown")).strip().lower()
#     if severity not in VALID_SEVERITIES:
#         severity = "unknown"
#     mechanism = (result.get("mechanism") or "").strip()
#     description = (result.get("description") or "").strip()
#     try:
#         confidence = float(result.get("confidence", 0.0))
#     except (TypeError, ValueError):
#         confidence = 0.0
#     confidence = max(0.0, min(1.0, confidence))

#     if found and (severity in {"none", "unknown"} or not description):
#         return {
#             "interaction_found": False, "severity": "unknown", "mechanism": "",
#             "description": ("Model output was inconsistent (an interaction was reported "
#                             "without a severity or explanation); treat as unverified."),
#             "confidence": 0.0,
#         }
#     if not found and severity != "unknown":
#         severity, mechanism, description = "none", "", ""
#     return {"interaction_found": found, "severity": severity,
#             "mechanism": mechanism, "description": description, "confidence": confidence}


# # if __name__ == "__main__":
# #     import asyncio
# #     import json
 
# #     logging.basicConfig(level=logging.INFO)
 
# #     async def _main():
# #         drugs = ["Warfarin", "Amoxicillin"]
# #         results = await analyze_all_interactions(drugs)
# #         print("\n=== Interaction Analysis Results ===")
# #         print(json.dumps(results, indent=2))
# #         with open("interaction_agent.json","w",encoding="UTF-8") as f:
# #             json.dump(results,f,indent=4)
 
# #     asyncio.run(_main())

"""
Drug Interaction Agent.

Pipeline for one drug pair:
  1. rxnav_client   -> resolve RxCUIs (for traceability)
  2. openfda_client -> fetch each drug's FDA label "Drug Interactions" text
  3. llm_client     -> ask the model whether either label describes an
                       interaction that applies to the other drug
  4. verify         -> reject anything the label text does not support

Why step 4 exists: FDA labels often describe interactions by drug CLASS
("oral anticoagulants", "azole antifungals") instead of naming the other
drug, and small local models return confident but contradictory JSON.
So the model must quote the label sentence that supports its answer, and
the code checks that the quote really appears in the label text. An
interaction that can't be verified is reported as "unknown", never as a
finding and never as "none" (which would read as safe).
"""

from __future__ import annotations

import itertools
import logging
import re

from core_engine.integrations.llm_client import call_llm_json
from core_engine.integrations.openfda_client import get_interaction_text
from core_engine.integrations.rxnav_client import get_rxcuis

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"contraindicated", "major", "moderate", "minor", "none"}
MAX_LABEL_CHARS = 8000   # per drug; needs num_ctx >= 8192 in llm_client
MIN_QUOTE_CHARS = 15     # a shorter "quote" is not meaningful evidence

EXTRACTION_PROMPT_TEMPLATE = """You are a clinical pharmacology assistant. Below is the official FDA label "Drug Interactions" text for two drugs. Decide whether EITHER label describes an interaction that applies to the OTHER drug.

An interaction can be described in two ways:
1. The label names the other drug directly.
2. The label refers to the other drug's CLASS instead of its name (for example "azole antifungals" covers fluconazole, "ACE inhibitors" covers lisinopril, "statins" covers atorvastatin). If the other drug belongs to a class named in a label, that counts.

Drug A: {drug_a}
Label text for Drug A:
\"\"\"
{text_a}
\"\"\"

Drug B: {drug_b}
Label text for Drug B:
\"\"\"
{text_b}
\"\"\"

Return a single JSON object with exactly these fields:
{{
  "interaction_found": true or false,
  "severity": one of "contraindicated", "major", "moderate", "minor", "none",
  "mechanism": "brief explanation of why they interact, or empty string",
  "description": "1-2 sentence plain-language explanation, or empty string",
  "evidence_quote": "ONE sentence copied EXACTLY from a label text above that supports your answer, or an empty string",
  "confidence": a number between 0.0 and 1.0
}}

Rules:
- Use ONLY the label text above. Do not use outside knowledge.
- If interaction_found is true you MUST give an evidence_quote copied word for word from the label text, and a severity other than "none".
- If neither label describes an interaction that applies to the other drug, set interaction_found to false, severity to "none", and evidence_quote to "".
- Return ONLY the JSON object, no markdown fences, no extra text.
"""

NO_LABEL_PLACEHOLDER = "(no FDA label interaction text was available for this drug)"


# --------------------------------------------------------------------------
# Verification helpers
# --------------------------------------------------------------------------

def _squash(text: str) -> str:
    """Normalise for comparison: unify quotes, collapse whitespace, lowercase."""
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def _quote_is_supported(quote: str, label_texts) -> bool:
    """
    True if `quote` really appears in one of the label texts.

    Tolerates whitespace/case/quote-mark differences, and quotes shortened with
    an ellipsis ("... may increase bleeding risk ..."): each fragment of at
    least MIN_QUOTE_CHARS characters must appear in the label text.
    """
    cleaned = _squash(quote or "").strip(" \"'")
    haystacks = [_squash(t) for t in label_texts if t]
    if not haystacks:
        return False

    fragments = [f.strip(" \"'.") for f in re.split(r"\.\.\.|\u2026", cleaned)]
    fragments = [f for f in fragments if len(f) >= MIN_QUOTE_CHARS]
    if not fragments:
        return False

    return all(any(fragment in h for h in haystacks) for fragment in fragments)


def _as_bool(value) -> bool:
    """bool("false") is True in Python, so strings from LLM JSON need real parsing."""
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def _unverified(reason: str) -> dict:
    return {
        "interaction_found": False,
        "severity": "unknown",
        "mechanism": "",
        "description": reason,
        "evidence": "",
        "confidence": 0.0,
    }


def _normalize_extraction(result: dict, label_texts=()) -> dict:
    """
    Clean the model's JSON and refuse to trust anything unsupported.

    A claimed interaction needs (a) a real severity, (b) an explanation and
    (c) -- when `label_texts` is given -- an evidence quote that truly appears
    in the label text. Otherwise it becomes severity "unknown" with
    confidence 0: unverified, not "none".
    """
    found = _as_bool(result.get("interaction_found", False))
    severity = str(result.get("severity", "unknown")).strip().lower()
    if severity not in VALID_SEVERITIES:
        severity = "unknown"
    mechanism = (result.get("mechanism") or "").strip()
    description = (result.get("description") or "").strip()
    evidence = (result.get("evidence_quote") or "").strip()
    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    if found and (severity in {"none", "unknown"} or not description):
        return _unverified(
            "Model output was inconsistent (an interaction was reported without a "
            "severity or explanation); treat as unverified."
        )

    if found and label_texts and not _quote_is_supported(evidence, label_texts):
        return _unverified(
            "The model reported an interaction but the evidence it cited was not found "
            "in the FDA label text; treat as unverified."
        )

    if not found and severity != "unknown":
        severity, mechanism, description, evidence = "none", "", "", ""

    return {
        "interaction_found": found,
        "severity": severity,
        "mechanism": mechanism,
        "description": description,
        "evidence": evidence if found else "",
        "confidence": confidence,
    }


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------

def _result(drug_a, drug_b, rxcuis, fields: dict, source: str) -> dict:
    return {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "rxcui_a": rxcuis.get(drug_a),
        "rxcui_b": rxcuis.get(drug_b),
        "interaction_found": fields["interaction_found"],
        "severity": fields["severity"],
        "mechanism": fields["mechanism"],
        "description": fields["description"],
        "evidence": fields.get("evidence", ""),
        "source": source,
        "confidence": fields["confidence"],
    }


async def analyze_interaction(drug_a: str, drug_b: str) -> dict:
    """
    Analyze the interaction between two drugs.

    Never raises for data problems: if label text is missing, the model fails,
    or its answer can't be verified, the result has severity "unknown".
    """
    rxcuis = await get_rxcuis([drug_a, drug_b])
    logger.info("Resolved RxCUIs: %s", rxcuis)

    text_a = await get_interaction_text(drug_a)
    text_b = await get_interaction_text(drug_b)

    if not text_a and not text_b:
        logger.warning("No FDA interaction text for '%s' or '%s'", drug_a, drug_b)
        return _result(drug_a, drug_b, rxcuis, _unverified(
            f"No FDA label interaction data available for {drug_a} or {drug_b}."
        ), "openfda")

    # One label is enough: it may describe the other drug's class.
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        drug_a=drug_a, text_a=(text_a or NO_LABEL_PLACEHOLDER)[:MAX_LABEL_CHARS],
        drug_b=drug_b, text_b=(text_b or NO_LABEL_PLACEHOLDER)[:MAX_LABEL_CHARS],
    )

    raw = await call_llm_json(prompt)
    if raw is None or not isinstance(raw, dict):
        logger.warning("LLM extraction failed or returned an unexpected shape for %s + %s", drug_a, drug_b)
        return _result(drug_a, drug_b, rxcuis, _unverified(
            "LLM extraction failed; unable to determine the interaction from the label text."
        ), "openfda+llm")

    # Verify the quote against exactly the text the model was shown.
    shown = tuple(t[:MAX_LABEL_CHARS] for t in (text_a, text_b) if t)
    normalized = _normalize_extraction(raw, shown)
    return _result(drug_a, drug_b, rxcuis, normalized, "openfda+llm")


async def analyze_all_interactions(drug_names: list[str]) -> list[dict]:
    """
    Analyze every pair in a list of 2+ drugs, one pair at a time (a local
    Ollama instance is compute-bound, so parallel calls would only queue).
    """
    if len(drug_names) < 2:
        logger.warning("Need at least 2 drugs to check interactions, got %d", len(drug_names))
        return []

    results = []
    for drug_a, drug_b in itertools.combinations(drug_names, 2):
        results.append(await analyze_interaction(drug_a, drug_b))
    return results


# ---- standalone test ----
# Run directly with: uv run python -m core_engine.agents.interaction_agent
if __name__ == "__main__":
    import asyncio
    import json

    logging.basicConfig(level=logging.INFO)

    async def _main():
        results = await analyze_all_interactions(["Warfarin", "Amoxicillin"])
        print(json.dumps(results, indent=2))

    asyncio.run(_main())