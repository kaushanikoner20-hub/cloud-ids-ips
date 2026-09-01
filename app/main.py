"""
FastAPI application entry point, configuration of routers and static files.
"""
from fastapi import FastAPI
from app.api import routes_health
from app.config import settings
from app.logging_config import setup_logging

def create_app() -> FastAPI:
    """
    FastAPI application factory.
    """
    setup_logging()

    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
    )

    # API v1 routes
    app.include_router(
        routes_health.router,
        prefix="/api/v1",
        tags=["Health"]
    )

    return app

app = create_app()
