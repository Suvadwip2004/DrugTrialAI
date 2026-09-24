from __future__ import annotations

import logging

from integrations.clinicaltrials_client import search_trials
from integrations.gemini_client import call_llm_json

logger = logging.getLogger(__name__)

MATCH_PROMPT_TEMPLATE = """You are a clinical trial eligibility assistant. Given a trial's eligibility criteria text and a patient's profile, determine how well the patient matches this trial.

Trial: {title} (NCT ID: {nct_id})
Eligibility Criteria:
\"\"\"
{eligibility_text}
\"\"\"

Patient Profile:
{patient_profile}

Return a single JSON object with exactly these fields:
{{
  "eligibility_match_score": a number between 0.0 and 1.0 (1.0 = clearly eligible, 0.0 = clearly excluded),
  "reason": "1-2 sentence explanation of the score, referencing specific criteria",
  "potential_concerns": "any exclusion criteria the patient might trigger, or empty string if none"
}}

Rules:
- Base the score ONLY on the eligibility criteria text and patient profile provided above.
- If the eligibility text is too vague/incomplete to judge, use a score around 0.5 and say so in "reason".
- Return ONLY the JSON object, no markdown fences, no extra commentary.
"""


def _format_patient_profile(patient_context: dict) -> str:
    if not patient_context:
        return "(no patient details provided — assess generically)"

    lines = []
    for key, value in patient_context.items():
        if value:
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines) if lines else "(no patient details provided)"


async def score_trial_match(trial: dict, patient_context: dict) -> dict:
    eligibility_text = trial.get("eligibility_criteria") or "(no eligibility criteria provided)"
    patient_profile = _format_patient_profile(patient_context)

    prompt = MATCH_PROMPT_TEMPLATE.format(
        title=trial.get("title", "Unknown trial"),
        nct_id=trial.get("nct_id", "Unknown"),
        eligibility_text=eligibility_text[:3000],  # cap for token control
        patient_profile=patient_profile,
    )

    result = await call_llm_json(prompt)

    if result is None or not isinstance(result, dict):
        logger.error("Eligibility scoring failed for trial %s", trial.get("nct_id"))
        enriched = dict(trial)
        enriched.update({
            "eligibility_match_score": 0.0,
            "reason": "Scoring failed — unable to assess eligibility match.",
            "potential_concerns": "",
        })
        return enriched

    enriched = dict(trial)
    enriched.update({
        "eligibility_match_score": float(result.get("eligibility_match_score", 0.0)),
        "reason": result.get("reason", ""),
        "potential_concerns": result.get("potential_concerns", ""),
    })
    return enriched


async def find_matching_trials(
    condition: str | None = None,
    drug_names: list[str] | None = None,
    patient_context: dict | None = None,
    phases: list[str] | None = None,
    status: str = "RECRUITING",
    max_trials: int = 5,
) -> list[dict]:
    intervention = drug_names[0] if drug_names else None
    patient_context = patient_context or {}

    trials = await search_trials(
        condition=condition,
        intervention=intervention,
        phases=phases,
        status=status,
        page_size=max_trials,
    )

    if not trials:
        logger.info("No trials found for condition='%s', intervention='%s'", condition, intervention)
        return []

    scored_trials = []
    for trial in trials:
        scored = await score_trial_match(trial, patient_context)
        scored_trials.append(scored)

    scored_trials.sort(key=lambda t: t["eligibility_match_score"], reverse=True)
    return scored_trials


# ---- standalone test ----
if __name__ == "__main__":
    import asyncio
    import json

    logging.basicConfig(level=logging.INFO)

    async def _main():
        patient_context = {
            "age": 68,
            "sex": "female",
            "renal_function": "moderate_impairment",
            "comorbidities": ["Chronic Kidney Disease Stage 3", "Hypertension"],
        }

        results = await find_matching_trials(
            condition="Atrial Fibrillation",
            drug_names=["Warfarin"],
            patient_context=patient_context,
            phases=["PHASE2", "PHASE3"],
            max_trials=3,
        )

        print(f"\n=== Found {len(results)} scored trial(s) ===")
        print(json.dumps(results, indent=2))

    asyncio.run(_main())