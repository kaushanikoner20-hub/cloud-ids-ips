"""Statistics response schemas. ARCHITECTURE.md Section 4.4."""

from pydantic import BaseModel


class StatsSummary(BaseModel):
    total_alerts: int
    active_threats: int
    blocked_ip_count: int
    events_ingested: int
