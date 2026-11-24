"""
DrugTrialAI Main Entrypoint.

Demonstrates the autonomous multi-agent analysis pipeline or runs a programmatic demo.
For command-line arguments and file outputs, see `run.py`.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from core_engine.agents.orchestrator import run_pipeline

logger = logging.getLogger("drugtrialai")


async def demo():
    print("=" * 70)
    print("DrugTrialAI: Autonomous Clinical Trial & Drug Interaction Analyzer")
    print("=" * 70)

    drugs = ["Warfarin", "Amoxicillin"]
    condition = "Atrial Fibrillation"
    patient_context = {
        "age": 68,
        "renal_function": "moderate_impairment",
        "comorbidities": ["Hypertension", "Chronic Kidney Disease"],
    }

    print(f"Drugs: {', '.join(drugs)}")
    print(f"Condition: {condition}")
    print(f"Patient context: {patient_context}")
    print("\nStarting multi-agent analysis pipeline...\n")

    result = await run_pipeline(
        drugs=drugs,
        condition=condition,
        patient_context=patient_context,
    )

    print("\n" + "=" * 70)
    print(result["report_md"])
    print("=" * 70)
    print(f"Validation Passed: {result['validated']}")
    print(f"Report Attempts: {result['report_attempts']}")
    if result["stage_errors"]:
        print("Stage Errors:", result["stage_errors"])


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
