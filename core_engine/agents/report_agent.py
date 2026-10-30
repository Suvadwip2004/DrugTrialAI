from __future__ import annotations

import logging

from core_engine.integrations.llm_client import call_llm

logger = logging.getLogger(__name__)

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


def _clinicaltrials_url(nct_id: str | None) -> str:
    return f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else ""


def _interaction_section(interactions: list[dict]) -> str:
    lines = ["## Drug Interaction Findings"]
    if not interactions:
        lines.append("_No interaction analysis was available._")
        return "\n".join(lines)

    for item in interactions:
        pair = f"{item.get('drug_a')} + {item.get('drug_b')}"
        severity = item.get("severity", "unknown")
        if not item.get("interaction_found"):
            lines.append(f"- **{pair}**: no interaction identified in FDA label text (severity: {severity}).")
            if item.get("description"):
                lines.append(f"  - Note: {item['description']}")
            continue

        lines.append(f"- **{pair}** — severity: **{severity}** (confidence {item.get('confidence', 0):.2f})")
        if item.get("mechanism"):
            lines.append(f"  - Mechanism: {item['mechanism']}")
        if item.get("description"):
            lines.append(f"  - Clinical note: {item['description']}")
        lines.append(f"  - Source: {item.get('source', 'unknown')}")
    return "\n".join(lines)


def _risk_section(risk: dict | None) -> str:
    lines = ["## Risk Assessment"]
    if not risk:
        lines.append("_No risk assessment was available._")
        return "\n".join(lines)

    lines.append(f"- **Risk level:** {risk.get('risk_level', 'unknown')}")
    lines.append(f"- **Composite score:** {risk.get('composite_risk_score', 'n/a')} / 10")
    if risk.get("hard_stop"):
        lines.append("- **HARD STOP:** a contraindicated combination was identified.")
    factors = risk.get("contributing_factors", [])
    if factors:
        lines.append("- **Contributing factors:**")
        lines.extend(f"  - {f}" for f in factors)
    if risk.get("explanation"):
        lines.append(f"\n{risk['explanation']}")
    return "\n".join(lines)


def _trials_section(trials: list[dict], max_trials: int = 5) -> str:
    lines = ["## Matching Clinical Trials"]
    if not trials:
        lines.append("_No matching recruiting trials were found for this query._")
        return "\n".join(lines)

    for trial in trials[:max_trials]:
        nct = trial.get("nct_id")
        phase = ", ".join(trial.get("phase") or []) or "n/a"
        score = trial.get("eligibility_match_score", 0.0)
        lines.append(f"- **[{nct}]({_clinicaltrials_url(nct)})** — {trial.get('title', 'Untitled')}")
        lines.append(f"  - Phase: {phase} | Status: {trial.get('status', 'n/a')} | Eligibility match: {score:.2f}")
        if trial.get("reason"):
            lines.append(f"  - Why: {trial['reason']}")
        if trial.get("potential_concerns"):
            lines.append(f"  - Possible exclusions: {trial['potential_concerns']}")
    return "\n".join(lines)


def _literature_section(literature: dict | None) -> str:
    lines = ["## Literature Evidence"]
    if not literature:
        lines.append("_No literature search was performed._")
        return "\n".join(lines)

    answer = literature.get("answer", "").strip()
    lines.append(answer or "_No answer available._")
    if not literature.get("grounded"):
        lines.append("\n>  This literature answer could not be fully verified against its sources. Treat with caution.")

    cited = literature.get("cited_sources", [])
    if cited:
        lines.append("\n**Cited papers:**")
        lines.extend(f"- [{s['title']}]({s['url']})" for s in cited)
    return "\n".join(lines)


def _build_facts_for_summary(
    drugs: list[str],
    condition: str | None,
    interactions: list[dict],
    risk: dict | None,
    trials: list[dict],
) -> str:
    facts = [f"Drugs reviewed: {', '.join(drugs)}"]
    if condition:
        facts.append(f"Condition: {condition}")
    for item in interactions:
        facts.append(
            f"Interaction {item.get('drug_a')} + {item.get('drug_b')}: "
            f"found={item.get('interaction_found')}, severity={item.get('severity')}"
        )
    if risk:
        facts.append(f"Risk level: {risk.get('risk_level')} (score {risk.get('composite_risk_score')}/10)")
        facts.append(f"Hard stop: {risk.get('hard_stop')}")
        facts.extend(f"Risk factor: {f}" for f in risk.get("contributing_factors", []))
    facts.append(f"Matching recruiting trials found: {len(trials)}")
    return "\n".join(facts)


def _fallback_summary(interactions: list[dict], risk: dict | None, trials: list[dict]) -> str:
    """Deterministic summary used if the LLM call fails."""
    parts = []
    if risk:
        parts.append(f"Overall risk level is {risk.get('risk_level', 'unknown')}.")
        if risk.get("hard_stop"):
            parts.append("A contraindicated combination was identified.")
    found = sum(1 for i in interactions if i.get("interaction_found"))
    parts.append(f"{found} of {len(interactions)} drug pair(s) showed an interaction.")
    parts.append(f"{len(trials)} matching trial(s) were found.")
    return " ".join(parts)


async def generate_report(
    drugs: list[str],
    condition: str | None = None,
    patient_context: dict | None = None,
    interactions: list[dict] | None = None,
    risk: dict | None = None,
    trials: list[dict] | None = None,
    literature: dict | None = None,
) -> dict:

    interactions = interactions or []
    trials = trials or []

    # 1. LLM writes only the summary, from facts we hand it.
    facts = _build_facts_for_summary(drugs, condition, interactions, risk, trials)
    try:
        summary = (await call_llm(SUMMARY_PROMPT_TEMPLATE.format(facts=facts))).strip()
        if not summary:
            raise ValueError("empty summary")
    except Exception as e:
        logger.error("Summary generation failed, using fallback: %s", e)
        summary = _fallback_summary(interactions, risk, trials)

    
    header = ["# Drug Interaction & Clinical Trial Report", ""]
    header.append(f"**Drugs:** {', '.join(drugs)}")
    if condition:
        header.append(f"**Condition:** {condition}")
    if patient_context:
        ctx = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in patient_context.items() if v)
        header.append(f"**Patient context:** {ctx}")

    sections = [
        "\n".join(header),
        DISCLAIMER,
        f"## Summary\n{summary}",
        _interaction_section(interactions),
        _risk_section(risk),
        _trials_section(trials),
        _literature_section(literature),
    ]
    report_md = "\n\n".join(sections) + "\n"

    # 3. Collect citations for the validator / audit trail.
    citations: list[dict] = []
    for item in interactions:
        if item.get("interaction_found"):
            citations.append({
                "type": "fda_label",
                "label": f"{item.get('drug_a')} + {item.get('drug_b')} ({item.get('source')})",
                "url": "",
            })
    for trial in trials:
        citations.append({
            "type": "clinical_trial",
            "label": f"{trial.get('nct_id')}: {trial.get('title', '')}",
            "url": _clinicaltrials_url(trial.get("nct_id")),
        })
    for src in (literature or {}).get("cited_sources", []):
        citations.append({"type": "pubmed", "label": src["title"], "url": src["url"]})

    return {"report_md": report_md, "summary": summary, "citations": citations}


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def _main():
        mock_interactions = [{
            "drug_a": "Warfarin", "drug_b": "Amoxicillin", "interaction_found": True,
            "severity": "moderate", "mechanism": "May alter gut flora affecting vitamin K synthesis",
            "description": "May potentiate anticoagulant effect and raise INR.",
            "source": "openfda+llm", "confidence": 0.8,
        }]
        mock_risk = {
            "composite_risk_score": 6.5, "risk_level": "elevated", "hard_stop": False,
            "contributing_factors": ["Warfarin + Amoxicillin: moderate severity interaction",
                                     "Age 68 is an independent risk factor (>=65)"],
            "explanation": "The score reflects a moderate interaction combined with age and renal impairment.",
        }
        mock_trials = [{
            "nct_id": "NCT00000000", "title": "Example anticoagulation study", "status": "RECRUITING",
            "phase": ["PHASE3"], "eligibility_match_score": 0.78,
            "reason": "Condition and age range match.", "potential_concerns": "",
        }]

        result = await generate_report(
            drugs=["Warfarin", "Amoxicillin"],
            condition="Atrial Fibrillation",
            patient_context={"age": 68, "renal_function": "moderate_impairment"},
            interactions=mock_interactions,
            risk=mock_risk,
            trials=mock_trials,
        )
        print(result["report_md"])

    asyncio.run(_main())