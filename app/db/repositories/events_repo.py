"""Repository for the ``events`` collection (ARCHITECTURE.md Section 5.1).

Owns the raw Mongo query/insert details for events so API routes and any
future detection code depend on this interface instead of the Motor
driver directly.
"""

from typing import Any, Optional

from pymongo.errors import DuplicateKeyError


class EventsRepository:
    def __init__(self, collection: Any) -> None:
        self._collection = collection

    async def insert(self, document: dict[str, Any]) -> bool:
        """Insert a raw event document.

        Returns ``True`` if the document was newly stored, ``False`` if
        an event with the same ``event_id``/``_id`` already exists
        (idempotent duplicate ingest per Section 1.4).
        """
        try:
            await self._collection.insert_one(document)
            return True
        except DuplicateKeyError:
            return False

    async def get_by_event_id(self, event_id: str) -> Optional[dict[str, Any]]:
        return await self._collection.find_one({"event_id": event_id})

    async def count(self) -> int:
        return await self._collection.count_documents({})

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self._collection.find().sort("received_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
