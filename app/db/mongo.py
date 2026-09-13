"""Motor (async) MongoDB client and connection lifecycle.

Per ARCHITECTURE.md Section 5: database name ``cloud_ids`` (env
``MONGO_DB``), indexes created at startup. Phase 0 only writes to the
``events`` collection, so only that collection's indexes are created here.
Later phases add their own collections/indexes to this module without
changing how routes obtain a database handle (see ``app.dependencies``).
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import Settings

logger = logging.getLogger(__name__)


class Mongo:
    """Thin wrapper holding the Motor client/database for the app lifespan."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None

    async def connect(self, settings: Settings) -> None:
        self.client = AsyncIOMotorClient(settings.mongo_uri)
        self.db = self.client[settings.mongo_db]
        await self.ensure_indexes()
        logger.info("mongo_connected", extra={"database": settings.mongo_db})

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("mongo_connection_closed")

    async def ping(self) -> bool:
        """Used by the readiness probe. Returns False instead of raising."""
        if self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:  # noqa: BLE001 - readiness probe must not raise
            logger.exception("mongo_ping_failed")
            return False

    async def ensure_indexes(self) -> None:
        if self.db is None:
            return
        events = self.db["events"]
        await events.create_index("event_id", unique=True)
        await events.create_index([("src_ip", 1), ("occurred_at", 1)])
        await events.create_index("received_at")


# Single instance shared across the app lifespan (set up in app.main's
# lifespan handler, torn down on shutdown).
mongo = Mongo()