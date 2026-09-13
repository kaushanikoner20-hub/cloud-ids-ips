"""NetworkEvent schema: the canonical ingest telemetry record.

Mirrors ARCHITECTURE.md Section 6 exactly. This is Phase 0 scope only:
no detection/ML/alert/IPS fields are part of this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Protocol

IPvAnyAddress = Union[IPv4Address, IPv6Address]
Port = Annotated[int, Field(ge=0, le=65535)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class EventLabels(BaseModel):
    """Simulator/test-only metadata. Never consumed by detectors."""

    scenario: str
    expected_attack: Optional[str] = None


class NetworkEvent(BaseModel):
    """Request body for ``POST /api/v1/events``."""

    event_id: Optional[UUID] = Field(
        default=None,
        description="Optional on ingest; server assigns a UUID if missing.",
    )
    occurred_at: datetime = Field(description="Client timestamp, ISO-8601 UTC.")

    src_ip: IPvAnyAddress
    dst_ip: IPvAnyAddress
    src_port: Port
    dst_port: Port
    protocol: Protocol

    http_method: Optional[str] = None
    http_path: Optional[str] = Field(default=None, max_length=256)
    http_status: Optional[int] = None

    bytes_in: NonNegativeInt
    bytes_out: NonNegativeInt
    duration_ms: NonNegativeInt

    auth_event: bool = False
    auth_success: Optional[bool] = None
    user_id: Optional[str] = None

    sensor_id: str = "default"

    labels: Optional[EventLabels] = None

    @field_validator("occurred_at")
    @classmethod
    def ensure_timezone_aware_utc(cls, value: datetime) -> datetime:
        """Normalize occurred_at to a timezone-aware UTC datetime.

        Naive datetimes are assumed to already be UTC (common for simulator
        clients); aware datetimes from other zones are converted to UTC.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class EventStored(NetworkEvent):
    """Shape of a document as persisted in the ``events`` collection."""

    event_id: UUID
    received_at: datetime


class IngestResult(BaseModel):
    """Response for ``POST /api/v1/events``.

    Phase 0 only populates ingest-acknowledgement fields. The remaining
    fields described in ARCHITECTURE.md Section 4.2 (``alert_created``,
    ``severity``, ``attack_types``, ``ml``, ``blocked``) belong to the
    detection pipeline and are intentionally not produced in this phase,
    since Phase 0 ingest must not run detection, ML, alerting, or IPS.
    """

    event_id: UUID
    accepted: bool
    received_at: datetime
