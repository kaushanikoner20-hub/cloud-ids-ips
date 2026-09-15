"""FastAPI application factory.

ARCHITECTURE.md Section 3: app.main creates the FastAPI app, handles
lifespan (Mongo connect, later: load/train ML, create indexes), and
mounts the static dashboard. No business logic lives here.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_alerts, routes_dashboard, routes_events, routes_health
from app.config import get_settings
from app.db.mongo import mongo
from app.logging_config import configure_logging

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    await mongo.connect(settings)
    yield
    await mongo.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Cloud IDS/IPS",
        description=(
            "Demonstration-grade cloud IDS/IPS. Simulated / authorized "
            "events only; see ARCHITECTURE.md for scope and limitations."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router, prefix="/api/v1")
    app.include_router(routes_events.router, prefix="/api/v1")
    app.include_router(routes_alerts.router, prefix="/api/v1")
    app.include_router(routes_dashboard.router, prefix="/api/v1")

    # Static dashboard assets (css/js) served under /static; keep "/" as
    # its own route (rather than mounting StaticFiles at "/") so it does
    # not shadow /docs or /redoc.
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()