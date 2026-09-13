import pytest


async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_ready(client):
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["mongo"] is True


async def test_dashboard_root_serves_html(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Cloud IDS/IPS" in resp.text


async def test_docs_available(client):
    resp = await client.get("/docs")
    assert resp.status_code == 200


async def test_openapi_available(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
