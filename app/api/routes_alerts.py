"""Alerts read API.

ARCHITECTURE.md Section 4.3. Phase 1 scope: read-only against a
collection nothing writes to yet (alert creation starts in Phase 2), so
every response here is an empty/zero result until then - that's the
correct behavior, not a bug.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.db.repositories.alerts_repo import AlertsRepository
from app.dependencies import get_alerts_repo
from app.schemas.alert import AlertListResponse, AlertOut
from app.schemas.common import AttackType, Severity

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[Severity] = None,
    attack_type: Optional[AttackType] = None,
    src_ip: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    alerts_repo: AlertsRepository = Depends(get_alerts_repo),
) -> AlertListResponse:
    items, total = await alerts_repo.list_alerts(
        severity=severity.value if severity else None,
        attack_type=attack_type.value if attack_type else None,
        src_ip=src_ip,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return AlertListResponse(
        items=[AlertOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/recent", response_model=list[AlertOut])
async def recent_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    alerts_repo: AlertsRepository = Depends(get_alerts_repo),
) -> list[AlertOut]:
    items = await alerts_repo.recent(limit=limit)
    return [AlertOut(**item) for item in items]
