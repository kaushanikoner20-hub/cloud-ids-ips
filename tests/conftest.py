"""Shared test fixtures.

Uses mongomock-motor so the test suite never requires a live MongoDB
instance (ARCHITECTURE.md Section 8.1 / 8.3 testing principles).
"""

import pytest
from mongomock_motor import AsyncMongoMockClient

import app.db.mongo as mongo_module
from app.main import create_app


@pytest.fixture
def _patch_motor_client(monkeypatch):
    """Redirect Mongo.connect() to an in-memory mongomock client."""
    monkeypatch.setattr(mongo_module, "AsyncIOMotorClient", AsyncMongoMockClient)
    yield


@pytest.fixture
async def client(_patch_motor_client):
    # _patch_motor_client is an explicit dependency (not autouse) so it is
    # guaranteed to run before create_app()'s lifespan calls Mongo.connect()
    # - fixture ordering between independent autouse fixtures is not
    # guaranteed by pytest.
    app = create_app()
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        async with app.router.lifespan_context(app):
            yield ac