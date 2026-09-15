"""Repository for the ``alerts`` collection (ARCHITECTURE.md Section 5.2).

Phase 1 only reads from this collection - nothing writes alerts until
the Phase 2 detection orchestrator exists, so every query here will
return an empty result against a fresh database. The query surface is
still built out now so ``GET /alerts`` has its real, final filtering
behavior from the start.
"""

from datetime import datetime
from typing import Any, Optional


class AlertsRepository:
    def __init__(self, collection: Any) -> None:
        self._collection = collection

    @staticmethod
    def _build_query(
        *,
        severity: Optional[str] = None,
        attack_type: Optional[str] = None,
        src_ip: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if severity is not None:
            query["severity"] = severity
        if attack_type is not None:
            query["attack_type"] = attack_type
        if src_ip is not None:
            query["src_ip"] = src_ip
        if since is not None or until is not None:
            created_at: dict[str, datetime] = {}
            if since is not None:
                created_at["$gte"] = since
            if until is not None:
                created_at["$lte"] = until
            query["created_at"] = created_at
        return query

    async def list_alerts(
        self,
        *,
        severity: Optional[str] = None,
        attack_type: Optional[str] = None,
        src_ip: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        query = self._build_query(
            severity=severity,
            attack_type=attack_type,
            src_ip=src_ip,
            since=since,
            until=until,
        )
        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        items = await cursor.to_list(length=limit)
        return items, total

    async def count(self, query: Optional[dict[str, Any]] = None) -> int:
        return await self._collection.count_documents(query or {})

    async def get_by_alert_id(self, alert_id: str) -> Optional[dict[str, Any]]:
        return await self._collection.find_one({"alert_id": alert_id})

    async def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self._collection.find().sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
