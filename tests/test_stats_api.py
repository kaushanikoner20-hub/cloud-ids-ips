from datetime import datetime, timezone


def _valid_event(**overrides):
    event = {
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "src_ip": "192.0.2.10",
        "dst_ip": "192.0.2.20",
        "src_port": 51234,
        "dst_port": 443,
        "protocol": "https",
        "bytes_in": 1024,
        "bytes_out": 2048,
        "duration_ms": 150,
    }
    event.update(overrides)
    return event


async def test_stats_summary_all_zero_on_fresh_db(client):
    resp = await client.get("/api/v1/stats/summary")
    assert resp.status_code == 200
    assert resp.json() == {
        "total_alerts": 0,
        "active_threats": 0,
        "blocked_ip_count": 0,
        "events_ingested": 0,
    }


async def test_stats_summary_events_ingested_reflects_real_count(client):
    await client.post("/api/v1/events", json=_valid_event())
    await client.post("/api/v1/events", json=_valid_event())
    await client.post("/api/v1/events", json=_valid_event())

    resp = await client.get("/api/v1/stats/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["events_ingested"] == 3
    # No detection exists yet in Phase 1, so these stay at zero even
    # though events were ingested.
    assert body["total_alerts"] == 0
    assert body["active_threats"] == 0
    assert body["blocked_ip_count"] == 0