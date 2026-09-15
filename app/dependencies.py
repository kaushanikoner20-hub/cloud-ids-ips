"""Shared FastAPI dependencies: DB access and demo token auth.

Per ARCHITECTURE.md Section 1.7: an optional ``API_TOKEN`` protects
mutating endpoints (e.g. ``POST /events``). If unset, the API is open
(local demo only).
"""

from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.db.mongo import mongo
from app.db.repositories.alerts_repo import AlertsRepository
from app.db.repositories.blocked_ips_repo import BlockedIpsRepository
from app.db.repositories.events_repo import EventsRepository
from app.services.stats_service import StatsService


def _get_collection(name: str) -> Any:
    if mongo.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not connected",
        )
    return mongo.db[name]


def get_events_collection() -> Any:
    """Return the ``events`` collection.

    Typed as ``Any`` rather than ``AsyncIOMotorCollection``: under tests
    this returns a mongomock-motor collection, not a real Motor one, and
    the two are not type-compatible even though their async APIs match.
    """
    return _get_collection("events")


def get_alerts_collection() -> Any:
    return _get_collection("alerts")


def get_blocked_ips_collection() -> Any:
    return _get_collection("blocked_ips")


def get_events_repo(collection: Any = Depends(get_events_collection)) -> EventsRepository:
    return EventsRepository(collection)


def get_alerts_repo(collection: Any = Depends(get_alerts_collection)) -> AlertsRepository:
    return AlertsRepository(collection)


def get_blocked_ips_repo(
    collection: Any = Depends(get_blocked_ips_collection),
) -> BlockedIpsRepository:
    return BlockedIpsRepository(collection)


def get_stats_service(
    events_repo: EventsRepository = Depends(get_events_repo),
    alerts_repo: AlertsRepository = Depends(get_alerts_repo),
    blocked_ips_repo: BlockedIpsRepository = Depends(get_blocked_ips_repo),
) -> StatsService:
    return StatsService(events_repo, alerts_repo, blocked_ips_repo)


def require_api_token(
    x_api_token: Optional[str] = Header(default=None, alias="X-API-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforce the demo API token on mutating endpoints, if configured.

    ``API_TOKEN=""`` (the default) leaves the endpoint open, matching the
    documented "empty = open (local demo only)" behavior.
    """
    if not settings.api_token:
        return
    if x_api_token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token",
        )