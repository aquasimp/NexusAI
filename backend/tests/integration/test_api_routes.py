"""Integration tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from nexus.main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "state" in data
    assert "system_health" in data

def test_api_system_info():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "llm" in data
    assert "ranker" in data
    assert "detector" in data
    assert "scenarios" in data
    assert "provenance" in data

def test_api_topology():
    response = client.get("/api/topology")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 9

def test_api_kb_search():
    response = client.get("/api/kb/search?q=postgres")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
