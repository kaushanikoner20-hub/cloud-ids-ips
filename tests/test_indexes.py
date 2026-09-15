"""Verifies Mongo.ensure_indexes() actually created the indexes required
by ARCHITECTURE.md Section 5 - not just that create_index() didn't raise.
"""


async def test_events_indexes(client):
    from app.db.mongo import mongo

    info = await mongo.db["events"].index_information()
    names = set(info.keys())

    assert any(
        info[name]["key"] == [("event_id", 1)] and info[name].get("unique")
        for name in names
    )
    assert any(
        info[name]["key"] == [("src_ip", 1), ("occurred_at", 1)] for name in names
    )
    assert any(info[name]["key"] == [("received_at", 1)] for name in names)


async def test_alerts_indexes(client):
    from app.db.mongo import mongo

    info = await mongo.db["alerts"].index_information()
    names = set(info.keys())

    assert any(
        info[name]["key"] == [("alert_id", 1)] and info[name].get("unique")
        for name in names
    )
    assert any(info[name]["key"] == [("created_at", 1)] for name in names)
    assert any(info[name]["key"] == [("severity", 1)] for name in names)
    assert any(info[name]["key"] == [("attack_type", 1)] for name in names)
    assert any(info[name]["key"] == [("src_ip", 1)] for name in names)
    assert any(
        info[name]["key"] == [("severity", 1), ("created_at", -1)] for name in names
    )


async def test_blocked_ips_indexes(client):
    from app.db.mongo import mongo

    info = await mongo.db["blocked_ips"].index_information()
    names = set(info.keys())

    assert any(info[name]["key"] == [("ip", 1), ("active", 1)] for name in names)
    assert any(info[name]["key"] == [("expires_at", 1)] for name in names)
    assert "ip_unique_active" in names
    assert info["ip_unique_active"].get("unique") is True