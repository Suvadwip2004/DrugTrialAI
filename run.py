"""
Command-line entrypoint for the Clinical Trial & Drug Interaction Analyzer.

Run from the project root:

    uv run python run.py --drugs Warfarin Amoxicillin \
        --condition "Atrial Fibrillation" --age 68 \
        --renal-function moderate_impairment

Writes report.md (readable) and report.json (full structured result) to the
current directory. Exits with code 1 if the report failed validation, so
scripts can detect it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from core_engine.agents.orchestrator import run_pipeline

RENAL_HEPATIC_CHOICES = ["normal", "mild_impairment", "moderate_impairment", "severe_impairment"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clinical Trial & Drug Interaction Analyzer")
    parser.add_argument("--drugs", nargs="+", required=True, help="Drug names, e.g. Warfarin Amoxicillin")
    parser.add_argument("--condition", help='Condition for trial search, e.g. "Atrial Fibrillation"')
    parser.add_argument("--age", type=int, help="Patient age in years")
    parser.add_argument("--renal-function", choices=RENAL_HEPATIC_CHOICES)
    parser.add_argument("--hepatic-function", choices=RENAL_HEPATIC_CHOICES)
    parser.add_argument("--comorbidities", nargs="*", help='e.g. "Hypertension" "Chronic Kidney Disease"')
    parser.add_argument("--phases", nargs="*", help="Trial phases, e.g. PHASE2 PHASE3")
    return parser


def build_patient_context(args: argparse.Namespace) -> dict:
    context = {
        "age": args.age,
        "renal_function": args.renal_function,
        "hepatic_function": args.hepatic_function,
        "comorbidities": args.comorbidities,
    }
    # Drop anything the user didn't provide.
    return {key: value for key, value in context.items() if value}


async def main() -> int:
    args = build_parser().parse_args()

    result = await run_pipeline(
        drugs=args.drugs,
        condition=args.condition,
        patient_context=build_patient_context(args),
        phases=[p.upper() for p in args.phases] if args.phases else None,
    )

    print("\n" + "=" * 70)
    print(result["report_md"])
    print("=" * 70)

    with open("report.md", "w", encoding="utf-8") as f:
        f.write(result["report_md"])
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Validated: {result['validated']}")
    print(f"Report attempts: {result['report_attempts']} (deterministic fallback summary used: {result['used_fallback_summary']})")
    if result["validation"]["errors"]:
        print("Validation errors:")
        for error in result["validation"]["errors"]:
            print(f"  - {error}")
    if result["stage_errors"]:
        print("Stage errors:")
        for error in result["stage_errors"]:
            print(f"  - {error}")
    print("Saved: report.md, report.json")

    return 0 if result["validated"] else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # httpx logs every request at INFO, which drowns out the pipeline's stage logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    sys.exit(asyncio.run(main()))