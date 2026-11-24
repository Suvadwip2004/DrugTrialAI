"""
Unit tests for core_engine/agents/validator_agent.py
"""

import pytest
from core_engine.agents.validator_agent import validate_report


SAMPLE_REPORT = """# Drug Interaction & Clinical Trial Report

**Drugs:** Warfarin, Amoxicillin
**Condition:** Atrial Fibrillation

> **Decision-support only.** This report summarizes retrieved FDA label text, published literature and registered trials. It is not medical advice and does not replace clinical judgment.

## Summary
The overall risk level is moderate with a score of 3.0. Zero of 1 pairs showed an interaction. One matching trial was found.

## Drug Interaction Findings
- **Warfarin + Amoxicillin**: no interaction identified in FDA label text (severity: none).

## Risk Assessment
- **Risk level:** moderate
- **Composite score:** 3.0 / 10

## Matching Clinical Trials
- **[NCT01234567](https://clinicaltrials.gov/study/NCT01234567)** — Example Trial

## Literature Evidence
No significant interaction reported.
"""


def test_validator_passes_on_compliant_report():
    drugs = ["Warfarin", "Amoxicillin"]
    interactions = [{"drug_a": "Warfarin", "drug_b": "Amoxicillin", "severity": "none", "interaction_found": False}]
    risk = {"risk_level": "moderate", "composite_risk_score": 3.0, "hard_stop": False}
    trials = [{"nct_id": "NCT01234567", "title": "Example Trial"}]

    result = validate_report(
        report_md=SAMPLE_REPORT,
        drugs=drugs,
        condition="Atrial Fibrillation",
        interactions=interactions,
        risk=risk,
        trials=trials,
    )
    assert result["passed"] is True
    assert result["errors"] == []


def test_validator_fails_missing_section():
    broken_report = SAMPLE_REPORT.replace("## Matching Clinical Trials", "")
    result = validate_report(
        report_md=broken_report,
        drugs=["Warfarin", "Amoxicillin"],
    )
    assert result["passed"] is False
    assert any("Missing report section" in e for e in result["errors"])


def test_validator_fails_missing_disclaimer():
    broken_report = SAMPLE_REPORT.replace("Decision-support only", "")
    result = validate_report(
        report_md=broken_report,
        drugs=["Warfarin", "Amoxicillin"],
    )
    assert result["passed"] is False
    assert any("disclaimer is missing" in e for e in result["errors"])


def test_validator_fails_fabricated_nct_id():
    broken_report = SAMPLE_REPORT.replace("NCT01234567", "NCT99999999")
    trials = [{"nct_id": "NCT01234567"}]
    result = validate_report(
        report_md=broken_report,
        drugs=["Warfarin", "Amoxicillin"],
        trials=trials,
    )
    assert result["passed"] is False
    assert any("NCT99999999" in e for e in result["errors"])


def test_validator_fails_mismatched_risk_level():
    risk = {"risk_level": "elevated", "composite_risk_score": 6.5, "hard_stop": False}
    result = validate_report(
        report_md=SAMPLE_REPORT,
        drugs=["Warfarin", "Amoxicillin"],
        risk=risk,
    )
    assert result["passed"] is False
    assert any("computed level is 'elevated'" in e for e in result["errors"])
