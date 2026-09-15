"""Aggregates counts from the repositories for ``GET /stats/summary``.

ARCHITECTURE.md Section 4.4 / module table: "app.services.stats_service |
Dashboard aggregates". Kept as a thin service (not a repository) since it
composes across three collections rather than owning one of them.
"""

from app.db.repositories.alerts_repo import AlertsRepository
from app.db.repositories.blocked_ips_repo import BlockedIpsRepository
from app.db.repositories.events_repo import EventsRepository
from app.schemas.stats import StatsSummary


class StatsService:
    def __init__(
        self,
        events_repo: EventsRepository,
        alerts_repo: AlertsRepository,
        blocked_ips_repo: BlockedIpsRepository,
    ) -> None:
        self._events_repo = events_repo
        self._alerts_repo = alerts_repo
        self._blocked_ips_repo = blocked_ips_repo

    async def summary(self) -> StatsSummary:
        events_ingested = await self._events_repo.count()
        total_alerts = await self._alerts_repo.count()

        # Section 4.4's full definition also bounds this to alerts created
        # within ACTIVE_THREAT_WINDOW_SECONDS. That setting isn't part of
        # app.config yet (it's introduced alongside detection thresholds
        # in a later phase), so the time bound is left out here; the
        # severity/status filter alone is accurate as long as no alerts
        # exist, which holds until Phase 2 adds alert creation.
        active_threats = await self._alerts_repo.count(
            {"severity": {"$in": ["medium", "high"]}, "status": {"$ne": "resolved"}}
        )

        blocked_ip_count = await self._blocked_ips_repo.count_active()

        return StatsSummary(
            total_alerts=total_alerts,
            active_threats=active_threats,
            blocked_ip_count=blocked_ip_count,
            events_ingested=events_ingested,
        )
