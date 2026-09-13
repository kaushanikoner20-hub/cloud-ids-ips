"""Liveness/readiness endpoints. ARCHITECTURE.md Section 4.1."""

from fastapi import APIRouter

from app.db.mongo import mongo

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness: process is up. No dependency checks."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict:
    """Readiness: Mongo ping succeeds.

    (ML model load will be added to this check in Phase 4.)
    """
    mongo_ok = await mongo.ping()
    ready = mongo_ok
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {"mongo": mongo_ok},
    }