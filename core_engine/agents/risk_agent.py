from __future__ import annotations
import logging
from core_engine.integrations.gemini_client import call_llm

logger  = logging.getLogger(__name__)


SEVERITY_WEIGHTS = {
    "contraindicated": 10.0,
    "major": 6.0,
    "moderate": 3.0,
    "minor": 1.0,
    "none": 0.0,
    "unknown": 1.5, 
}



RENAL_HEPATIC_WEIGHTS = {
    "normal": 0.0,
    "mild_impairment": 0.5,
    "moderate_impairment": 1.5,
    "severe_impairment": 3.0,
}

AGE_HIGH_RISK_THRESHOLD = 65
AGE_RISK_POINTS = 1.0
COMORBIDITY_POINTS_EACH = 0.5
COMORBIDITY_POINTS_CAP = 2.0  # don't let a long comorbidity list dominate the score
 
MAX_SCORE = 10.0
 
 
EXPLANATION_PROMPT_TEMPLATE = """You are a clinical risk communication assistant. Given the following structured risk assessment data, write a 2-3 sentence plain-language explanation for a clinician of WHY the risk score is what it is. Do not invent any facts not present in the data below — only explain/summarize what's given.
 
Risk Assessment Data:
{risk_data}
 
Return only the explanation text, no headers, no markdown, no extra commentary.
"""
 

def _score_interactions(interactions: list[dict]) -> tuple[float, bool, list[str]]:
    score = 0.0
    hard_stop  = False
    notes  = []

    for interaction in interactions:
        severity  = interaction.get("severity","unknown")
        weight = SEVERITY_WEIGHTS.get(severity,SEVERITY_WEIGHTS["unknown"])
        score += weight

        if severity == "contraindicated":
            hard_stop = True
            notes.append(
                f"HARD STOP: {interaction.get('drug_a')} + {interaction.get('drug_b')} "
                f"is contraindicated ({interaction.get('description', 'no description')})"
            )
        elif interaction.get("interaction_found") and severity in ("major", "moderate"):
            notes.append(
                f"{interaction.get('drug_a')} + {interaction.get('drug_b')}: "
                f"{severity} severity interaction"
            )

    return score, hard_stop, notes

 
def _score_patient_context(patient_context: dict) -> tuple[float, list[str]]:
    # pass
    score = 0.0
    notes  = []

    if not patient_context :
        return score,notes

    age = patient_context.get("age")
    if isinstance(age,(int,float)) and age >= AGE_HIGH_RISK_THRESHOLD:
        score += AGE_RISK_POINTS
        notes.append(f"Age {age} is an independent risk factor (≥{AGE_HIGH_RISK_THRESHOLD})")

    renal = patient_context.get("renal_function", "normal")
    renal_weight = RENAL_HEPATIC_WEIGHTS.get(renal, 0.0)

    if renal_weight > 0:
        score += renal_weight
        notes.append(f"Renal function: {renal}")

 
    hepatic = patient_context.get("hepatic_function", "normal")
    hepatic_weight = RENAL_HEPATIC_WEIGHTS.get(hepatic, 0.0)
    if hepatic_weight > 0:
        score += hepatic_weight
        notes.append(f"Hepatic function: {hepatic}")
 
    comorbidities = patient_context.get("comorbidities", [])
    if comorbidities:
        comorbidity_score = min(len(comorbidities) * COMORBIDITY_POINTS_EACH, COMORBIDITY_POINTS_CAP)
        score += comorbidity_score
        notes.append(f"Comorbidities noted: {', '.join(comorbidities)}")
 
    return score, notes
 

def _risk_level_from_score(score: float) -> str:
    if score >= 8.0:
        return "critical"
    elif score >= 5.0:
        return "elevated"
    elif score >= 2.0:
        return "moderate"
    else:
        return "low"
 
async def assess_risk(interactions: list[dict],patient_context: dict | None = None,include_llm_explanation: bool = True) -> dict:
    patient_context = patient_context or {}

    interaction_score, hard_stop, interaction_notes = _score_interactions(interactions)
    patient_score, patient_notes = _score_patient_context(patient_context)
 
    raw_score = interaction_score + patient_score
    composite_score = min(raw_score, MAX_SCORE)

    if hard_stop:
        composite_score  = MAX_SCORE

    risk_level = "critical" if hard_stop else _risk_level_from_score(composite_score)
    contributing_factors = interaction_notes + patient_notes 

    if not contributing_factors:
        contributing_factors = ["No significant interaction or patient-specific risk factors identified."]

 
    result = {
        "composite_risk_score": round(composite_score, 2),
        "risk_level": risk_level,
        "hard_stop": hard_stop,
        "contributing_factors": contributing_factors,
        "explanation": "",
    }
 
    if include_llm_explanation:
        prompt  = EXPLANATION_PROMPT_TEMPLATE.format(risk_data = result)
        try:
            print("llm calling ")
            explanation  =await call_llm(prompt)
            print("llm call done")
            result["explanation"] = explanation.strip()
        except Exception as e:
            logger.error("Risk explanation generation failed: %s", e)
            result["explanation"] = "Explanation unavailable due to some intetrnal problem ."
    return result






if __name__ == "__main__":
    import asyncio
    import json
    logging.basicConfig(level=logging.INFO,filemode="app.log")
    async def main():
                
        mock_interactions = [
            {
                "drug_a": "Warfarin",
                "drug_b": "Amoxicillin",
                "interaction_found": True,
                "severity": "moderate",
                "mechanism": "Alters gut flora affecting vitamin K synthesis",
                "description": "May potentiate anticoagulant effect, increasing bleeding risk.",
                "source": "openfda+gemini",
                "confidence": 0.85,
            }
        ]

        patient_context = {
            "age": 68,
            "renal_function": "moderate_impairment",
            "comorbidities": ["Chronic Kidney Disease Stage 3", "Hypertension"],
        }
 
        result = await assess_risk(mock_interactions, patient_context)
        # print(json.dumps(result, indent=2))
        with open ("risk_agent.json","w",encoding="UTF-8") as f:
            json.dump(result,f,indent=4)



    asyncio.run(main())