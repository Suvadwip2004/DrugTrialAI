"""
Unit tests for FastAPI backend routes.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DrugTrialAI API"
    assert data["status"] == "online"
    assert "/docs" in data["docs_url"]


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "services" in data


def test_analyze_endpoint_validation_error():
    # Empty drug list should return 422 Unprocessable Entity
    response = client.post("/api/v1/analyze", json={"drugs": []})
    assert response.status_code == 422


def test_trials_search_missing_params():
    # Must provide at least 'condition' or 'intervention'
    response = client.get("/api/v1/trials/search")
    assert response.status_code == 400
    assert "Must provide at least" in response.json()["detail"]


def test_drug_interactions_minimum_drugs():
    # Requires at least 2 drugs
    response = client.post("/api/v1/drugs/interactions", json={"drugs": ["Warfarin"]})
    assert response.status_code == 422
