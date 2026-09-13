"""Shared FastAPI dependencies: DB access and demo token auth.

Per ARCHITECTURE.md Section 1.7: an optional ``API_TOKEN`` protects
mutating endpoints (e.g. ``POST /events``). If unset, the API is open
(local demo only).
"""

from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.db.mongo import mongo


def get_events_collection() -> Any:
    """Return the ``events`` collection.

    Typed as ``Any`` rather than ``AsyncIOMotorCollection``: under tests
    this returns a mongomock-motor collection, not a real Motor one, and
    the two are not type-compatible even though their async APIs match.
    """
    if mongo.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not connected",
        )
    return mongo.db["events"]


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