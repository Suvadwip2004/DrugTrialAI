"""
Pydantic Schemas for Request, Response, and Data Models.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PatientContext(BaseModel):
    age: int | None = Field(default=None, description="Patient age in years", ge=0, le=130)
    sex: str | None = Field(default=None, description="Patient biological sex (male, female, other)")
    renal_function: str | None = Field(
        default="normal",
        description="One of: normal, mild_impairment, moderate_impairment, severe_impairment",
    )
    hepatic_function: str | None = Field(
        default="normal",
        description="One of: normal, mild_impairment, moderate_impairment, severe_impairment",
    )
    comorbidities: list[str] = Field(default_factory=list, description="List of patient conditions/comorbidities")


class AnalysisRequest(BaseModel):
    drugs: list[str] = Field(..., min_length=1, description="List of drug names to analyze (e.g. ['Warfarin', 'Amoxicillin'])")
    condition: str | None = Field(default=None, description="Medical condition for clinical trial matching")
    patient_context: PatientContext | None = Field(default=None, description="Patient clinical parameters")
    phases: list[str] | None = Field(default=None, description="Clinical trial phases to filter (e.g. ['PHASE2', 'PHASE3'])")


class InteractionItem(BaseModel):
    drug_a: str
    drug_b: str
    rxcui_a: str | None = None
    rxcui_b: str | None = None
    interaction_found: bool
    severity: str
    mechanism: str
    description: str
    evidence: str = ""
    source: str
    confidence: float


class RiskAssessment(BaseModel):
    composite_risk_score: float
    risk_level: str
    hard_stop: bool
    contributing_factors: list[str] = Field(default_factory=list)
    explanation: str


class TrialItem(BaseModel):
    nct_id: str | None = None
    title: str | None = None
    status: str | None = None
    phase: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    eligibility_match_score: float = 0.0
    reason: str = ""
    potential_concerns: str = ""


class CitationItem(BaseModel):
    type: str
    label: str
    url: str = ""


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    drugs: list[str]
    condition: str | None = None
    interaction_analysis: list[dict[str, Any]] = Field(default_factory=list)
    risk_assessment: dict[str, Any] | None = None
    matching_trials: list[dict[str, Any]] = Field(default_factory=list)
    literature: dict[str, Any] | None = None
    report_md: str
    summary: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    validation: dict[str, Any]
    validated: bool
    report_attempts: int
    used_fallback_summary: bool
    stage_errors: list[str] = Field(default_factory=list)
