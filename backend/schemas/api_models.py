"""
API Request and Response Models.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from core_engine.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    CitationItem,
    InteractionItem,
    PatientContext,
    RiskAssessment,
    TrialItem,
    ValidationResult,
)

__all__ = [
    "AnalysisRequest",
    "AnalysisResponse",
    "CitationItem",
    "InteractionItem",
    "PatientContext",
    "RiskAssessment",
    "TrialItem",
    "ValidationResult",
    "HealthResponse",
    "DrugInteractionRequest",
    "TrialSearchRequest",
]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    engine: str = "DrugTrialAI Multi-Agent Core"
    services: dict[str, str] = Field(default_factory=dict)


class DrugInteractionRequest(BaseModel):
    drugs: list[str] = Field(..., min_length=2, description="At least two drug names to check interactions between")


class TrialSearchRequest(BaseModel):
    condition: str | None = Field(default=None, description="Medical condition, e.g. 'Atrial Fibrillation'")
    intervention: str | None = Field(default=None, description="Drug or intervention name, e.g. 'Warfarin'")
    phases: list[str] | None = Field(default=None, description="List of phases, e.g. ['PHASE2', 'PHASE3']")
    status: str = Field(default="RECRUITING", description="Recruitment status")
    page_size: int = Field(default=10, ge=1, le=50)
