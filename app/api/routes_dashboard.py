"""Dashboard-facing JSON endpoints.

ARCHITECTURE.md Section 4.4. Phase 1 scope: only ``/stats/summary``.
The other stats endpoints listed in Section 4.4 (attack-distribution,
severity-distribution, trends, top-sources) depend on alerts existing
and are added once Phase 2 creates them.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_stats_service
from app.schemas.stats import StatsSummary
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummary)
async def stats_summary(
    stats_service: StatsService = Depends(get_stats_service),
) -> StatsSummary:
    return await stats_service.summary()