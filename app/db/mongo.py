"""Motor (async) MongoDB client and connection lifecycle.

Per ARCHITECTURE.md Section 5: database name ``cloud_ids`` (env
``MONGO_DB``), indexes created at startup. Phase 1 adds the ``alerts``
and ``blocked_ips`` collections' indexes (no documents are written to
them yet - that starts in Phase 2/3). ``create_index`` is idempotent:
Mongo no-ops if an identical index already exists, so this is safe to
run on every startup.
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

        alerts = self.db["alerts"]
        await alerts.create_index("alert_id", unique=True)
        await alerts.create_index("created_at")
        await alerts.create_index("severity")
        await alerts.create_index("attack_type")
        await alerts.create_index("src_ip")
        # Compound index for the dashboard's common filter combination
        # (ARCHITECTURE.md Section 5.2: "compound for dashboard filters").
        await alerts.create_index([("severity", 1), ("created_at", -1)])

        blocked_ips = self.db["blocked_ips"]
        await blocked_ips.create_index([("ip", 1), ("active", 1)])
        await blocked_ips.create_index("expires_at")
        # Uniqueness only applies among *active* blocks: the same IP may
        # have multiple historical (inactive) block records over time.
        await blocked_ips.create_index(
            "ip",
            unique=True,
            partialFilterExpression={"active": True},
            name="ip_unique_active",
        )


# Single instance shared across the app lifespan (set up in app.main's
# lifespan handler, torn down on shutdown).
mongo = Mongo()