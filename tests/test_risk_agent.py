"""
Unit tests for core_engine/agents/risk_agent.py
"""

import pytest
from core_engine.agents.risk_agent import (
    _score_interactions,
    _score_patient_context,
    assess_risk,
    SEVERITY_WEIGHTS,
    RENAL_HEPATIC_WEIGHTS,
)


def test_severity_weights_values():
    assert SEVERITY_WEIGHTS["contraindicated"] == 10.0
    assert SEVERITY_WEIGHTS["major"] == 6.0
    assert SEVERITY_WEIGHTS["moderate"] == 3.0
    assert SEVERITY_WEIGHTS["minor"] == 1.0
    assert SEVERITY_WEIGHTS["none"] == 0.0


def test_score_interactions_contraindicated_triggers_hard_stop():
    interactions = [
        {"drug_a": "DrugA", "drug_b": "DrugB", "severity": "contraindicated", "interaction_found": True, "description": "Lethal"}
    ]
    score, hard_stop, notes = _score_interactions(interactions)
    assert score == 10.0
    assert hard_stop is True
    assert any("HARD STOP" in note for note in notes)


def test_score_interactions_multiple_pairs():
    interactions = [
        {"drug_a": "DrugA", "drug_b": "DrugB", "severity": "major", "interaction_found": True},
        {"drug_a": "DrugB", "drug_b": "DrugC", "severity": "minor", "interaction_found": True},
    ]
    score, hard_stop, notes = _score_interactions(interactions)
    assert score == 7.0
    assert hard_stop is False


def test_score_patient_context_empty():
    score, notes = _score_patient_context({})
    assert score == 0.0
    assert notes == []


def test_score_patient_context_age_threshold():
    score_young, _ = _score_patient_context({"age": 64})
    assert score_young == 0.0

    score_old, notes_old = _score_patient_context({"age": 65})
    assert score_old == 1.0
    assert any("Age 65" in note for note in notes_old)


def test_score_patient_context_renal_and_hepatic():
    ctx = {
        "renal_function": "moderate_impairment",
        "hepatic_function": "severe_impairment",
    }
    score, notes = _score_patient_context(ctx)
    assert score == 1.5 + 3.0
    assert len(notes) == 2


def test_score_patient_context_comorbidities_capped():
    ctx = {
        "comorbidities": ["C1", "C2", "C3", "C4", "C5", "C6"],
    }
    score, notes = _score_patient_context(ctx)
    # 6 * 0.5 = 3.0, but capped at 2.0
    assert score == 2.0
    assert any("Comorbidities noted" in note for note in notes)


async def test_assess_risk_critical_hard_stop(monkeypatch):
    async def fake_call_llm(prompt):
        return "Explanation of contraindication."

    monkeypatch.setattr("core_engine.agents.risk_agent.call_llm", fake_call_llm)

    interactions = [{"drug_a": "A", "drug_b": "B", "severity": "contraindicated", "interaction_found": True}]
    result = await assess_risk(interactions, {})
    assert result["risk_level"] == "critical"
    assert result["hard_stop"] is True
    assert result["composite_risk_score"] == 10.0


async def test_assess_risk_score_clamped_at_max(monkeypatch):
    async def fake_call_llm(prompt):
        return "Explanation"

    monkeypatch.setattr("core_engine.agents.risk_agent.call_llm", fake_call_llm)

    interactions = [
        {"drug_a": "A", "drug_b": "B", "severity": "major", "interaction_found": True},
        {"drug_a": "B", "drug_b": "C", "severity": "major", "interaction_found": True},
    ]
    # 6.0 + 6.0 = 12.0 -> clamped at 10.0
    result = await assess_risk(interactions, {"age": 70})
    assert result["composite_risk_score"] == 10.0
