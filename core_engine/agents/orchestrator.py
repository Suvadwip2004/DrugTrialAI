"""
Orchestrator (LangGraph).

Runs every agent as one pipeline with a validate-and-retry loop:

    check_interactions -> assess_risk -> find_trials -> search_literature
                                                              |
                                                        write_report <---+
                                                              |          |
                                                          validate --retry
                                                              |
                                                             END

Design decisions:
  - Stages run SEQUENTIALLY, not in parallel. Everything LLM-related runs on
    one local Ollama instance, which is compute-bound; parallel calls would
    just queue and make logs harder to follow.
  - A failure in one stage does not kill the run. The error is recorded in
    `stage_errors` and the pipeline continues with whatever it has.
  - If validation fails, the report is regenerated (up to
    MAX_LLM_SUMMARY_ATTEMPTS times with the LLM summary). After that it falls
    back ONCE to the deterministic summary, which is built from the data and
    passes the validator's summary checks by construction.
  - If validation still fails (e.g. a data problem regeneration can't fix),
    the report is returned with a loud failure banner, never silently released.

NOTE: LangGraph does not allow a node name to equal a state key, which is why
nodes are named like "assess_risk" while the state key is "risk".
"""

from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from core_engine.agents.interaction_agent import analyze_all_interactions
from core_engine.agents.rag_agent import answer_question
from core_engine.agents.report_agent import generate_report
from core_engine.agents.risk_agent import assess_risk
from core_engine.agents.trial_matching_agent import find_matching_trials
from core_engine.agents.validator_agent import validate_report

logger = logging.getLogger(__name__)

MAX_LLM_SUMMARY_ATTEMPTS = 2


class PipelineState(TypedDict, total=False):
    # inputs
    drugs: list[str]
    condition: str | None
    patient_context: dict
    phases: list[str] | None
    # agent outputs
    interactions: list[dict]
    risk: dict | None
    trials: list[dict]
    literature: dict | None
    report: dict
    validation: dict
    # bookkeeping
    report_attempts: int
    used_fallback_summary: bool
    stage_errors: list[str]


def _with_error(state: PipelineState, stage: str, exc: Exception) -> list[str]:
    msg = f"{stage} failed: {exc}"
    logger.error(msg)
    return state.get("stage_errors", []) + [msg]


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

async def node_check_interactions(state: PipelineState) -> dict:
    logger.info("Stage 1/6: checking drug interactions")
    try:
        interactions = await analyze_all_interactions(state["drugs"])
        return {"interactions": interactions}
    except Exception as e:
        return {"interactions": [], "stage_errors": _with_error(state, "Interaction analysis", e)}


async def node_assess_risk(state: PipelineState) -> dict:
    logger.info("Stage 2/6: assessing risk")
    try:
        risk = await assess_risk(state.get("interactions", []), state.get("patient_context") or {})
        return {"risk": risk}
    except Exception as e:
        return {"risk": None, "stage_errors": _with_error(state, "Risk assessment", e)}


async def node_find_trials(state: PipelineState) -> dict:
    logger.info("Stage 3/6: searching clinical trials")
    condition = state.get("condition")
    if not condition:
        logger.info("No condition given; skipping trial search")
        return {"trials": []}
    try:
        trials = await find_matching_trials(
            condition=condition,
            drug_names=state["drugs"],
            patient_context=state.get("patient_context") or {},
            phases=state.get("phases"),
        )
        return {"trials": trials}
    except Exception as e:
        return {"trials": [], "stage_errors": _with_error(state, "Trial matching", e)}


def _sanitize_literature(literature: dict) -> dict:
    """
    If the model cited sources that were never retrieved, discard the answer
    rather than let the validator hard-fail the whole report. Regenerating the
    report cannot fix a bad literature answer, so handle it at the source.
    """
    if literature.get("invalid_citations"):
        logger.warning("Discarding literature answer with invalid citations: %s", literature["invalid_citations"])
        literature = dict(literature)
        literature.update({
            "answer": "The literature answer was discarded because it cited sources that were not retrieved.",
            "grounded": False,
            "cited_sources": [],
            "invalid_citations": [],
        })
    return literature


async def node_search_literature(state: PipelineState) -> dict:
    logger.info("Stage 4/6: searching literature")
    drugs = state["drugs"]
    question = (
        f"What is known about interactions between {', '.join(drugs)}, "
        f"including mechanism and clinical significance?"
    )
    try:
        literature = await answer_question(question, drug_names=drugs)
        return {"literature": _sanitize_literature(literature)}
    except Exception as e:
        return {"literature": None, "stage_errors": _with_error(state, "Literature search", e)}


async def node_write_report(state: PipelineState) -> dict:
    attempts = state.get("report_attempts", 0)
    use_llm = attempts < MAX_LLM_SUMMARY_ATTEMPTS
    logger.info(
        "Stage 5/6: writing report (attempt %d, %s summary)",
        attempts + 1, "LLM" if use_llm else "deterministic",
    )
    try:
        report = await generate_report(
            drugs=state["drugs"],
            condition=state.get("condition"),
            patient_context=state.get("patient_context") or {},
            interactions=state.get("interactions", []),
            risk=state.get("risk"),
            trials=state.get("trials", []),
            literature=state.get("literature"),
            use_llm_summary=use_llm,
        )
        return {"report": report, "report_attempts": attempts + 1, "used_fallback_summary": not use_llm}
    except Exception as e:
        # generate_report has its own fallbacks, so reaching here is unexpected.
        # Mark the fallback as used so the retry loop ends instead of spinning.
        return {
            "report": {"report_md": "", "summary": "", "citations": []},
            "report_attempts": attempts + 1,
            "used_fallback_summary": True,
            "stage_errors": _with_error(state, "Report generation", e),
        }


async def node_validate(state: PipelineState) -> dict:
    logger.info("Stage 6/6: validating report")
    validation = validate_report(
        report_md=state["report"]["report_md"],
        drugs=state["drugs"],
        condition=state.get("condition"),
        patient_context=state.get("patient_context") or {},
        interactions=state.get("interactions", []),
        risk=state.get("risk"),
        trials=state.get("trials", []),
        literature=state.get("literature"),
    )
    return {"validation": validation}


def route_after_validation(state: PipelineState) -> str:
    if state["validation"]["passed"]:
        return "done"
    if state.get("used_fallback_summary"):
        logger.warning("Validation failed even with the deterministic summary; giving up.")
        return "done"
    logger.warning("Validation failed (%s); regenerating report", state["validation"]["errors"])
    return "retry"


# --------------------------------------------------------------------------
# Graph
# --------------------------------------------------------------------------

def build_graph():
    builder = StateGraph(PipelineState)

    builder.add_node("check_interactions", node_check_interactions)
    builder.add_node("assess_risk", node_assess_risk)
    builder.add_node("find_trials", node_find_trials)
    builder.add_node("search_literature", node_search_literature)
    builder.add_node("write_report", node_write_report)
    builder.add_node("validate", node_validate)

    builder.add_edge(START, "check_interactions")
    builder.add_edge("check_interactions", "assess_risk")
    builder.add_edge("assess_risk", "find_trials")
    builder.add_edge("find_trials", "search_literature")
    builder.add_edge("search_literature", "write_report")
    builder.add_edge("write_report", "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validation,
        {"retry": "write_report", "done": END},
    )
    return builder.compile()


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

async def run_pipeline(
    drugs: list[str],
    condition: str | None = None,
    patient_context: dict | None = None,
    phases: list[str] | None = None,
) -> dict:
    """
    Run the full analysis and return a validated report.

    `phases` uses ClinicalTrials.gov values, e.g. ["PHASE2", "PHASE3"].

    Returns a dict with: drugs, condition, interaction_analysis, risk_assessment,
    matching_trials, literature, report_md, summary, citations, validation,
    validated (bool), report_attempts, used_fallback_summary, stage_errors.
    """
    drugs = [d.strip() for d in drugs if d and d.strip()]
    if not drugs:
        raise ValueError("At least one drug name is required.")

    final = await _get_graph().ainvoke({
        "drugs": drugs,
        "condition": condition,
        "patient_context": patient_context or {},
        "phases": phases,
        "report_attempts": 0,
        "stage_errors": [],
    })

    validation = final["validation"]
    stage_errors = final.get("stage_errors", [])
    report_md = final["report"]["report_md"]

    # Never release a failed report silently.
    if not validation["passed"]:
        banner = ["> ⚠️ **VALIDATION FAILED — do not rely on this report.**"]
        banner.extend(f"> - {e}" for e in validation["errors"])
        report_md = "\n".join(banner) + "\n\n" + report_md

    notes = list(validation["warnings"]) + [f"Pipeline stage error: {e}" for e in stage_errors]
    if notes:
        report_md += "\n## Validation Notes\n" + "\n".join(f"- {n}" for n in notes) + "\n"

    return {
        "drugs": drugs,
        "condition": condition,
        "interaction_analysis": final.get("interactions", []),
        "risk_assessment": final.get("risk"),
        "matching_trials": final.get("trials", []),
        "literature": final.get("literature"),
        "report_md": report_md,
        "summary": final["report"]["summary"],
        "citations": final["report"]["citations"],
        "validation": validation,
        "validated": validation["passed"],
        "report_attempts": final.get("report_attempts", 0),
        "used_fallback_summary": final.get("used_fallback_summary", False),
        "stage_errors": stage_errors,
    }


# ---- standalone test ----
# Run directly with: uv run python -m core_engine.agents.orchestrator
if __name__ == "__main__":
    import asyncio
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    async def _main():
        result = await run_pipeline(
            drugs=["Warfarin", "Amoxicillin"],
            condition="Atrial Fibrillation",
            patient_context={
                "age": 68,
                "renal_function": "moderate_impairment",
                "comorbidities": ["Chronic Kidney Disease Stage 3", "Hypertension"],
            },
        )
        print("\n" + "=" * 70)
        print(result["report_md"])
        print("=" * 70)
        print(json.dumps({
            "validated": result["validated"],
            "report_attempts": result["report_attempts"],
            "used_fallback_summary": result["used_fallback_summary"],
            "errors": result["validation"]["errors"],
            "warnings": result["validation"]["warnings"],
            "stage_errors": result["stage_errors"],
        }, indent=2))

    asyncio.run(_main())