"""
Integration tests for the health endpoint.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """
    Verify that GET /api/v1/health returns 200 OK with expected JSON.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "cloud-ids-ips-api"
    }
