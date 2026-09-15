"""Alert response schemas.

Mirrors the ``alerts`` collection shape from ARCHITECTURE.md Section 5.2.
Phase 1 only *reads* this collection (always empty, since nothing creates
alerts until Phase 2's detection orchestrator exists) - these models
exist now so ``GET /alerts`` has a stable, documented response contract
from the start rather than being redefined later.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import AttackType, Severity


class RuleHit(BaseModel):
    rule_id: str
    name: str
    severity: Severity
    evidence: dict[str, Any] = {}


class MLInfo(BaseModel):
    is_anomaly: bool
    score: float
    threshold: float
    top_features: list[dict[str, Any]] = []


class AlertOut(BaseModel):
    """Shape of one alert as returned by the read APIs."""

    alert_id: UUID
    event_id: str
    created_at: datetime
    src_ip: str
    dst_ip: str
    severity: Severity
    attack_type: AttackType
    attack_types: list[AttackType] = []
    title: str
    description: str
    rule_hits: list[RuleHit] = []
    ml: Optional[MLInfo] = None
    status: str = "open"
    ips_action: str = "none"
    blocked_ip_id: Optional[str] = None


class AlertListResponse(BaseModel):
    items: list[AlertOut]
    total: int
    limit: int
    offset: int
