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


async def test_ingest_valid_event_returns_ack_and_stores_document(client):
    resp = await client.post("/api/v1/events", json=_valid_event())
    assert resp.status_code == 201
    body = resp.json()
    assert body["accepted"] is True
    assert "event_id" in body
    assert "received_at" in body

    # Detection must not run in Phase 0: response has no alert/severity/
    # ml/blocked fields at all.
    assert "alert_created" not in body
    assert "severity" not in body
    assert "ml" not in body
    assert "blocked" not in body


async def test_ingest_generates_event_id_when_missing(client):
    resp = await client.post("/api/v1/events", json=_valid_event())
    assert resp.status_code == 201
    assert resp.json()["event_id"] is not None


async def test_ingest_respects_provided_event_id(client):
    given_id = "11111111-1111-1111-1111-111111111111"
    resp = await client.post("/api/v1/events", json=_valid_event(event_id=given_id))
    assert resp.status_code == 201
    assert resp.json()["event_id"] == given_id


async def test_duplicate_event_id_is_not_double_stored(client):
    given_id = "22222222-2222-2222-2222-222222222222"
    first = await client.post("/api/v1/events", json=_valid_event(event_id=given_id))
    assert first.status_code == 201
    assert first.json()["accepted"] is True

    second = await client.post("/api/v1/events", json=_valid_event(event_id=given_id))
    assert second.status_code == 200  # nothing created on the duplicate
    assert second.json()["accepted"] is False


async def test_invalid_ip_returns_422(client):
    resp = await client.post("/api/v1/events", json=_valid_event(src_ip="not-an-ip"))
    assert resp.status_code == 422


async def test_negative_bytes_returns_422(client):
    resp = await client.post("/api/v1/events", json=_valid_event(bytes_in=-1))
    assert resp.status_code == 422


async def test_out_of_range_port_returns_422(client):
    resp = await client.post("/api/v1/events", json=_valid_event(dst_port=70000))
    assert resp.status_code == 422


async def test_sensor_id_defaults_and_document_is_stored(client):
    from app.db.mongo import mongo

    resp = await client.post("/api/v1/events", json=_valid_event())
    assert resp.status_code == 201
    event_id = resp.json()["event_id"]

    doc = await mongo.db["events"].find_one({"event_id": event_id})
    assert doc is not None
    assert doc["sensor_id"] == "default"
    assert doc["protocol"] == "https"