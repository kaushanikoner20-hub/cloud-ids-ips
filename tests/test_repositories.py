"""Repository tests, run against mongomock (see tests/conftest.py).

Uses the ``client`` fixture purely to get a connected ``mongo.db``
(via the app's lifespan) - these tests exercise the repositories
directly, not the HTTP layer.
"""

from app.db.repositories.alerts_repo import AlertsRepository
from app.db.repositories.blocked_ips_repo import BlockedIpsRepository
from app.db.repositories.events_repo import EventsRepository


async def test_events_repo_insert_and_get_by_event_id(client):
    from app.db.mongo import mongo

    repo = EventsRepository(mongo.db["events"])
    doc = {"_id": "e1", "event_id": "e1", "src_ip": "192.0.2.1"}

    inserted = await repo.insert(doc)
    assert inserted is True

    found = await repo.get_by_event_id("e1")
    assert found is not None
    assert found["src_ip"] == "192.0.2.1"


async def test_events_repo_duplicate_insert_returns_false(client):
    from app.db.mongo import mongo

    repo = EventsRepository(mongo.db["events"])
    doc = {"_id": "e2", "event_id": "e2"}

    assert await repo.insert(doc) is True
    assert await repo.insert(doc) is False


async def test_events_repo_count(client):
    from app.db.mongo import mongo

    repo = EventsRepository(mongo.db["events"])
    assert await repo.count() == 0

    await repo.insert({"_id": "e3", "event_id": "e3"})
    await repo.insert({"_id": "e4", "event_id": "e4"})
    assert await repo.count() == 2


async def test_alerts_repo_returns_empty_on_fresh_db(client):
    from app.db.mongo import mongo

    repo = AlertsRepository(mongo.db["alerts"])

    items, total = await repo.list_alerts()
    assert items == []
    assert total == 0

    assert await repo.recent() == []
    assert await repo.count() == 0
    assert await repo.get_by_alert_id("does-not-exist") is None


async def test_blocked_ips_repo_basic_lifecycle(client):
    from app.db.mongo import mongo

    repo = BlockedIpsRepository(mongo.db["blocked_ips"])

    assert await repo.is_blocked("192.0.2.99") is False
    assert await repo.count_active() == 0

    await repo.upsert_block("192.0.2.99", reason="test", severity="high")
    assert await repo.is_blocked("192.0.2.99") is True
    assert await repo.count_active() == 1

    active = await repo.get_active()
    assert len(active) == 1
    assert active[0]["ip"] == "192.0.2.99"

    unblocked = await repo.unblock("192.0.2.99", reason="test cleanup")
    assert unblocked is True
    assert await repo.is_blocked("192.0.2.99") is False
    assert await repo.count_active() == 0