async def test_list_alerts_empty(client):
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}


async def test_list_alerts_with_filters_still_empty(client):
    resp = await client.get(
        "/api/v1/alerts",
        params={"severity": "high", "attack_type": "port_scan", "src_ip": "192.0.2.1"},
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_list_alerts_respects_limit_offset_params(client):
    resp = await client.get("/api/v1/alerts", params={"limit": 5, "offset": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 5
    assert body["offset"] == 10


async def test_recent_alerts_empty(client):
    resp = await client.get("/api/v1/alerts/recent")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_invalid_severity_returns_422(client):
    resp = await client.get("/api/v1/alerts", params={"severity": "catastrophic"})
    assert resp.status_code == 422
