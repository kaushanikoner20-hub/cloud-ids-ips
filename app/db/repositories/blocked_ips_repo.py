"""Repository for the ``blocked_ips`` collection (ARCHITECTURE.md Section 5.3).

Phase 1 scope: persistence methods only. Nothing calls ``upsert_block``
yet - auto-blocking on high-severity alerts is wired up in Phase 3
(the ``Blocker``/``demo_blocker`` abstraction). These methods exist now
so the ``blocked_ip_count`` stat has a real (always-zero-for-now)
source instead of a hardcoded value.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional


class BlockedIpsRepository:
    def __init__(self, collection: Any) -> None:
        self._collection = collection

    async def upsert_block(
        self,
        ip: str,
        reason: str,
        severity: str,
        source: str = "manual",
        ttl_seconds: int = 3600,
        alert_id: Optional[str] = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        document = {
            "ip": ip,
            "active": True,
            "reason": reason,
            "severity": severity,
            "enforcement": "simulated",
            "source": source,
            "created_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
            "alert_id": alert_id,
            "unblocked_at": None,
            "unblock_reason": None,
        }
        await self._collection.update_one(
            {"ip": ip, "active": True},
            {"$set": document},
            upsert=True,
        )
        return document

    async def get_active(self) -> list[dict[str, Any]]:
        cursor = self._collection.find({"active": True})
        return await cursor.to_list(length=None)

    async def is_blocked(self, ip: str) -> bool:
        doc = await self._collection.find_one({"ip": ip, "active": True})
        return doc is not None

    async def count_active(self) -> int:
        return await self._collection.count_documents({"active": True})

    async def unblock(self, ip: str, reason: Optional[str] = None) -> bool:
        """Deactivate the active block for ``ip``. Returns False if none existed."""
        result = await self._collection.update_one(
            {"ip": ip, "active": True},
            {
                "$set": {
                    "active": False,
                    "unblocked_at": datetime.now(timezone.utc),
                    "unblock_reason": reason,
                }
            },
        )
        return result.modified_count > 0
