"""
Tests for core_engine/agents/interaction_agent.py

Label text and model answers are made up and injected with monkeypatch, so no
network, Ollama or real drug label is involved. What is tested is the agent's
safety behaviour: it must never turn a bad, contradictory or unsupported model
answer into either a finding or a "none".
"""

import pytest

from core_engine.agents import interaction_agent
from core_engine.agents.interaction_agent import (
    _normalize_extraction,
    _quote_is_supported,
    analyze_all_interactions,
    analyze_interaction,
)

LABEL_A = "Concurrent use with oral anticoagulants may increase the risk of bleeding. Monitor closely."
LABEL_B = "No interactions with other medicines have been described."
QUOTE = "Concurrent use with oral anticoagulants may increase the risk of bleeding."


def good_answer(**overrides):
    answer = {
        "interaction_found": True,
        "severity": "moderate",
        "mechanism": "Class-level label warning",
        "description": "May increase bleeding risk.",
        "evidence_quote": QUOTE,
        "confidence": 0.8,
    }
    answer.update(overrides)
    return answer


# --------------------------------------------------------------------------
# _quote_is_supported
# --------------------------------------------------------------------------

def test_exact_quote_is_supported():
    assert _quote_is_supported(QUOTE, [LABEL_A])


def test_quote_ignores_case_whitespace_and_surrounding_quotes():
    messy = '  "concurrent   USE with oral anticoagulants\nmay increase the risk of bleeding." '
    assert _quote_is_supported(messy, [LABEL_A])


def test_quote_supported_when_found_in_either_label():
    assert _quote_is_supported(QUOTE, [LABEL_B, LABEL_A])


def test_ellipsis_quote_requires_each_fragment_to_appear():
    assert _quote_is_supported("Concurrent use with oral anticoagulants ... increase the risk of bleeding", [LABEL_A])
    assert not _quote_is_supported("Concurrent use with oral anticoagulants ... causes liver failure in children", [LABEL_A])


@pytest.mark.parametrize("quote", ["", "   ", "too short", None])
def test_empty_or_tiny_quote_is_not_evidence(quote):
    assert not _quote_is_supported(quote, [LABEL_A])


def test_invented_quote_is_not_supported():
    assert not _quote_is_supported("This drug is dangerous when combined with anything.", [LABEL_A])


def test_no_label_text_means_nothing_is_supported():
    assert not _quote_is_supported(QUOTE, [])
    assert not _quote_is_supported(QUOTE, [None, ""])


# --------------------------------------------------------------------------
# _normalize_extraction
# --------------------------------------------------------------------------

def test_contradictory_output_is_flagged_not_trusted():
    # The exact shape that appeared in a real run.
    out = _normalize_extraction({
        "interaction_found": True,
        "severity": "none",
        "mechanism": "",
        "description": "",
        "confidence": 1.0,
    })
    assert out["interaction_found"] is False
    assert out["severity"] == "unknown"
    assert out["confidence"] == 0.0
    assert "inconsistent" in out["description"].lower()


def test_found_without_description_is_flagged():
    out = _normalize_extraction(good_answer(description="   "))
    assert out["severity"] == "unknown"
    assert out["interaction_found"] is False


def test_invalid_severity_with_found_true_is_flagged():
    out = _normalize_extraction(good_answer(severity="catastrophic"))
    assert out["severity"] == "unknown"
    assert out["interaction_found"] is False


def test_verified_finding_is_kept_with_its_evidence():
    out = _normalize_extraction(good_answer(), (LABEL_A, LABEL_B))
    assert out["interaction_found"] is True
    assert out["severity"] == "moderate"
    assert out["evidence"] == QUOTE
    assert out["confidence"] == pytest.approx(0.8)


def test_unsupported_evidence_makes_a_finding_unverified():
    out = _normalize_extraction(good_answer(evidence_quote="Made up sentence about bleeding risk."), (LABEL_A,))
    assert out["interaction_found"] is False
    assert out["severity"] == "unknown"
    assert "not found" in out["description"]


def test_missing_evidence_makes_a_finding_unverified():
    out = _normalize_extraction(good_answer(evidence_quote=""), (LABEL_A,))
    assert out["severity"] == "unknown"


def test_not_found_forces_severity_none_and_clears_text():
    out = _normalize_extraction({
        "interaction_found": False,
        "severity": "major",
        "mechanism": "leftover",
        "description": "leftover",
        "evidence_quote": "leftover",
        "confidence": 0.7,
    }, (LABEL_A,))
    assert out["severity"] == "none"
    assert out["mechanism"] == out["description"] == out["evidence"] == ""


@pytest.mark.parametrize("raw", ["false", "False", "no"])
def test_string_false_is_not_treated_as_true(raw):
    # bool("false") is True in Python -- a classic trap with LLM JSON.
    out = _normalize_extraction({
        "interaction_found": raw,
        "severity": "moderate",
        "mechanism": "m",
        "description": "d",
        "confidence": 0.5,
    })
    assert out["interaction_found"] is False
    assert out["severity"] == "none"


@pytest.mark.parametrize("raw, expected", [(7, 1.0), (-2, 0.0), ("high", 0.0), (None, 0.0), (0.42, 0.42)])
def test_confidence_is_clamped_to_zero_one(raw, expected):
    out = _normalize_extraction({"interaction_found": False, "severity": "none", "confidence": raw})
    assert out["confidence"] == pytest.approx(expected)


def test_none_text_fields_do_not_crash():
    out = _normalize_extraction(good_answer(mechanism=None))
    assert out["mechanism"] == ""
    assert out["interaction_found"] is True


# --------------------------------------------------------------------------
# analyze_interaction (full flow with fakes)
# --------------------------------------------------------------------------

@pytest.fixture
def fakes(monkeypatch):
    """Install fake services and return a state dict the tests can configure."""
    state = {"labels": {"A": LABEL_A, "B": LABEL_B}, "answer": good_answer(), "llm_calls": []}

    async def fake_rxcuis(names):
        return {n: f"rx-{n}" for n in names}

    async def fake_text(name):
        return state["labels"].get(name)

    async def fake_llm(prompt):
        state["llm_calls"].append(prompt)
        return state["answer"]

    monkeypatch.setattr(interaction_agent, "get_rxcuis", fake_rxcuis)
    monkeypatch.setattr(interaction_agent, "get_interaction_text", fake_text)
    monkeypatch.setattr(interaction_agent, "call_llm_json", fake_llm)
    return state


async def test_verified_class_level_interaction_is_reported(fakes):
    result = await analyze_interaction("A", "B")
    assert result["interaction_found"] is True
    assert result["severity"] == "moderate"
    assert result["evidence"] == QUOTE
    assert result["source"] == "openfda+llm"
    assert result["rxcui_a"] == "rx-A"


async def test_hallucinated_interaction_is_downgraded_to_unknown(fakes):
    fakes["answer"] = good_answer(evidence_quote="The label says these two must never be combined.")
    result = await analyze_interaction("A", "B")
    assert result["interaction_found"] is False
    assert result["severity"] == "unknown"


async def test_contradictory_model_output_becomes_unknown_not_none(fakes):
    fakes["answer"] = {
        "interaction_found": True,
        "severity": "none",
        "mechanism": "",
        "description": "",
        "confidence": 1.0,
    }
    result = await analyze_interaction("A", "B")
    assert result["severity"] == "unknown"
    assert result["confidence"] == 0.0


async def test_no_label_text_for_either_drug_skips_the_llm(fakes):
    fakes["labels"] = {}
    result = await analyze_interaction("A", "B")
    assert result["severity"] == "unknown"
    assert fakes["llm_calls"] == []


async def test_one_label_is_enough_to_ask_the_model(fakes):
    fakes["labels"] = {"A": LABEL_A}  # B has no label at all
    result = await analyze_interaction("A", "B")
    assert len(fakes["llm_calls"]) == 1
    assert "no FDA label interaction text was available" in fakes["llm_calls"][0]
    assert result["interaction_found"] is True


async def test_llm_returning_none_gives_unknown(fakes):
    fakes["answer"] = None
    result = await analyze_interaction("A", "B")
    assert result["severity"] == "unknown"
    assert "failed" in result["description"].lower()


async def test_llm_returning_a_list_gives_unknown(fakes):
    fakes["answer"] = [{"interaction_found": True}]
    result = await analyze_interaction("A", "B")
    assert result["severity"] == "unknown"


async def test_label_text_is_capped_in_the_prompt(fakes):
    fakes["labels"] = {"A": LABEL_A + (" filler" * 5000), "B": LABEL_B}
    await analyze_interaction("A", "B")
    assert len(fakes["llm_calls"][0]) < 2 * interaction_agent.MAX_LABEL_CHARS + 3000


# --------------------------------------------------------------------------
# analyze_all_interactions
# --------------------------------------------------------------------------

@pytest.mark.parametrize("drugs", [[], ["OnlyOne"]])
async def test_fewer_than_two_drugs_returns_empty(drugs):
    assert await analyze_all_interactions(drugs) == []


async def test_three_drugs_make_three_pairs(monkeypatch):
    seen = []

    async def fake_analyze(a, b):
        seen.append((a, b))
        return {"drug_a": a, "drug_b": b}

    monkeypatch.setattr(interaction_agent, "analyze_interaction", fake_analyze)
    results = await analyze_all_interactions(["X", "Y", "Z"])
    assert seen == [("X", "Y"), ("X", "Z"), ("Y", "Z")]
    assert len(results) == 3
