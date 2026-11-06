from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

REQUIRED_SECTIONS = [
    "## Summary",
    "## Drug Interaction Findings",
    "## Risk Assessment",
    "## Matching Clinical Trials",
    "## Literature Evidence",
]
DISCLAIMER_MARKER = "Decision-support only"
RISK_LEVELS = {"low", "moderate", "elevated", "critical"}

# Common drug-name endings, used to spot drug names in free text.
# Heuristic only: it catches most generic names, not all of them.
DRUG_SUFFIX_PATTERN = re.compile(
    r"\b[a-z]{3,}(?:cillin|farin|pril|sartan|statin|olol|azole|mycin|cycline|"
    r"oxacin|prazole|dipine|afil|mab|tinib|parin|xaban|gatran|formin|gliptin|"
    r"floxacin|vir|zepam|triptan|setron)\b",
    re.IGNORECASE,
)


def _numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _normalize_number(n: str) -> str:
    """'6.50' and '6.5' should compare equal; so should '10' and '10.0'."""
    try:
        return f"{float(n):g}"
    except ValueError:
        return n


def _source_text(drugs, condition, patient_context, interactions, risk, trials, literature) -> str:
    """Everything the report is allowed to draw from, flattened to lowercase text."""
    blob = json.dumps(
        {
            "drugs": drugs,
            "condition": condition,
            "patient_context": patient_context,
            "interactions": interactions,
            "risk": risk,
            "trials": trials,
            "literature": literature,
        },
        default=str,
    )
    return blob.lower()


def _extract_summary(report_md: str) -> str:
    match = re.search(r"## Summary\s*\n(.*?)(?=\n## |\Z)", report_md, re.DOTALL)
    return match.group(1).strip() if match else ""


def validate_report(
    report_md: str,
    drugs: list[str],
    condition: str | None = None,
    patient_context: dict | None = None,
    interactions: list[dict] | None = None,
    risk: dict | None = None,
    trials: list[dict] | None = None,
    literature: dict | None = None,
) -> dict:
    """
    Validate `report_md` against the source data.

    Returns:
        {
            "passed": bool,          # True only if there are no errors
            "errors": [str],         # must be fixed before release
            "warnings": [str],       # shown, but don't block release
            "checks": {name: bool},  # per-check pass/fail, for the audit trail
        }
    """
    interactions = interactions or []
    trials = trials or []
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    summary = _extract_summary(report_md)
    source_text = _source_text(drugs, condition, patient_context, interactions, risk, trials, literature)

    # 1. Structure ------------------------------------------------------------
    missing = [s for s in REQUIRED_SECTIONS if s not in report_md]
    checks["sections_present"] = not missing
    if missing:
        errors.append(f"Missing report section(s): {', '.join(missing)}")

    checks["disclaimer_present"] = DISCLAIMER_MARKER in report_md
    if not checks["disclaimer_present"]:
        errors.append("Medical disclaimer is missing from the report.")

    checks["summary_present"] = bool(summary)
    if not summary:
        errors.append("Summary section is empty.")

    # 2. Trial IDs: every NCT number in the report must come from the trial data
    known_ncts = {str(t.get("nct_id", "")).upper() for t in trials}
    report_ncts = {n.upper() for n in re.findall(r"NCT\d{8}", report_md, re.IGNORECASE)}
    fabricated_ncts = sorted(report_ncts - known_ncts)
    checks["trial_ids_valid"] = not fabricated_ncts
    if fabricated_ncts:
        errors.append(f"Report mentions trial ID(s) not returned by any agent: {', '.join(fabricated_ncts)}")

    # 3. Numbers in the summary must exist in the source data -----------------
    allowed_numbers = {_normalize_number(n) for n in _numbers_in(source_text)}
    allowed_numbers |= {"10", str(len(interactions)), str(len(trials))}
    allowed_numbers |= {str(sum(1 for i in interactions if i.get("interaction_found")))}
    unsupported = sorted(
        n for n in _numbers_in(summary) if _normalize_number(n) not in allowed_numbers
    )
    checks["summary_numbers_supported"] = not unsupported
    if unsupported:
        errors.append(f"Summary contains number(s) not found in the source data: {', '.join(unsupported)}")

    # 4. Summary risk level must match the computed one -----------------------
    if risk:
        actual_level = str(risk.get("risk_level", "")).lower()
        claimed_levels = set()
        for m in re.finditer(r"\b(low|moderate|elevated|critical)\s+(?:overall\s+)?risk\b", summary, re.IGNORECASE):
            claimed_levels.add(m.group(1).lower())
        for m in re.finditer(r"risk(?:\s+level)?\s+(?:is|of|was)\s+(low|moderate|elevated|critical)\b", summary, re.IGNORECASE):
            claimed_levels.add(m.group(1).lower())
        wrong = sorted(l for l in claimed_levels if l != actual_level)
        checks["summary_risk_level_matches"] = not wrong
        if wrong:
            errors.append(
                f"Summary states risk level '{', '.join(wrong)}' but the computed level is '{actual_level}'."
            )

        # 5. Hard-stop consistency
        hard_stop = bool(risk.get("hard_stop"))
        claims_contra = bool(re.search(r"contraindicat|hard stop", summary, re.IGNORECASE))
        if claims_contra and not hard_stop:
            checks["hard_stop_consistent"] = False
            errors.append("Summary claims a contraindication/hard stop, but none was identified by the risk agent.")
        elif hard_stop and not claims_contra:
            checks["hard_stop_consistent"] = False
            warnings.append("A hard stop was triggered but the summary does not mention it.")
        else:
            checks["hard_stop_consistent"] = True
    else:
        warnings.append("No risk assessment supplied; risk consistency checks were skipped.")

    # 6. Drug names in the summary must appear somewhere in the source data ---
    unknown_drugs = sorted(
        {m.group(0).lower() for m in DRUG_SUFFIX_PATTERN.finditer(summary)
         if m.group(0).lower() not in source_text}
    )
    checks["summary_drugs_supported"] = not unknown_drugs
    if unknown_drugs:
        errors.append(f"Summary mentions drug name(s) not found in the source data: {', '.join(unknown_drugs)}")

    # 7. Every interaction pair must be reported -------------------------------
    unreported = [
        f"{i.get('drug_a')} + {i.get('drug_b')}"
        for i in interactions
        if f"{i.get('drug_a')} + {i.get('drug_b')}" not in report_md
    ]
    checks["all_interactions_reported"] = not unreported
    if unreported:
        errors.append(f"Interaction pair(s) missing from the report: {', '.join(unreported)}")

    # 8. Literature grounding --------------------------------------------------
    if literature:
        invalid = literature.get("invalid_citations", [])
        checks["literature_no_fake_citations"] = not invalid
        if invalid:
            errors.append(f"Literature answer cites non-existent source number(s): {invalid}")

        all_urls = {s.get("url") for s in literature.get("all_sources", [])}
        stray = [s["url"] for s in literature.get("cited_sources", []) if s.get("url") not in all_urls]
        checks["literature_sources_verifiable"] = not stray
        if stray:
            errors.append(f"Literature cites source(s) that were never retrieved: {stray}")

        insufficient = "does not contain enough information" in literature.get("answer", "").lower()
        if not literature.get("grounded") and not insufficient and literature.get("answer"):
            warnings.append("Literature answer is not fully grounded in its cited sources.")
    else:
        warnings.append("No literature evidence supplied.")

    # 9. Data-quality warnings -------------------------------------------------
    unknown = [f"{i.get('drug_a')} + {i.get('drug_b')}" for i in interactions if i.get("severity") == "unknown"]
    if unknown:
        warnings.append(f"Interaction data unavailable for: {', '.join(unknown)}")
    low_conf = [
        f"{i.get('drug_a')} + {i.get('drug_b')}" for i in interactions
        if i.get("interaction_found") and float(i.get("confidence", 1.0)) < 0.5
    ]
    if low_conf:
        warnings.append(f"Low-confidence interaction finding(s): {', '.join(low_conf)}")

    passed = not errors
    if not passed:
        logger.warning("Report validation failed with %d error(s): %s", len(errors), errors)

    return {"passed": passed, "errors": errors, "warnings": warnings, "checks": checks}


# ---- standalone test ----
# Run directly with: uv run python -m core_engine.agents.validator_agent
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,filename="app.log")

    drugs = ["Warfarin", "Amoxicillin"]
    interactions = [{
        "drug_a": "Warfarin", "drug_b": "Amoxicillin", "interaction_found": True,
        "severity": "moderate", "mechanism": "May alter gut flora", "description": "May raise INR.",
        "source": "openfda+llm", "confidence": 0.8,
    }]
    risk = {
        "composite_risk_score": 6.5, "risk_level": "elevated", "hard_stop": False,
        "contributing_factors": ["Warfarin + Amoxicillin: moderate severity interaction",
                                 "Age 68 is an independent risk factor (>=65)"],
        "explanation": "",
    }
    trials = [{"nct_id": "NCT00000000", "title": "Example study", "status": "RECRUITING",
               "phase": ["PHASE3"], "eligibility_match_score": 0.78}]

    def build_report(summary: str) -> str:
        return (
            "# Drug Interaction & Clinical Trial Report\n\n"
            "> **Decision-support only.** Not medical advice.\n\n"
            f"## Summary\n{summary}\n\n"
            "## Drug Interaction Findings\n- **Warfarin + Amoxicillin** severity moderate\n\n"
            "## Risk Assessment\n- Risk level: elevated\n\n"
            "## Matching Clinical Trials\n- NCT00000000 Example study\n\n"
            "## Literature Evidence\n_No literature search was performed._\n"
        )

    good_summary = (
        "The overall risk level is elevated at a score of 6.5 out of 10. Warfarin and "
        "Amoxicillin show a moderate interaction. 1 matching trial was found."
    )
    bad_summary = (
        "The overall risk is critical with a score of 9.2. Warfarin and Amoxicillin are "
        "contraindicated, and Ciprofloxacin should also be avoided. See NCT99999999."
    )

    for label, summary in [("GOOD", good_summary), ("BAD (tampered)", bad_summary)]:
        result = validate_report(
            build_report(summary), drugs, "Atrial Fibrillation", {"age": 68},
            interactions, risk, trials, literature=None,
        )
        print(f"\n=== {label} summary ===")
        print(json.dumps(result, indent=2))
        with open("validator_agent.json","w",encoding="UTF-8") as f:
            json.dump(result,f,indent=4)