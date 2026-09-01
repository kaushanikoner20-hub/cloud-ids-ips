"""
API endpoints for system health and readiness checks.
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Liveness probe: reports if the API process is running.
    """
    return {
        "status": "ok",
        "service": "cloud-ids-ips-api"
    }
