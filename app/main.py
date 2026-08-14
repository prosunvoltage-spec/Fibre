"""FastAPI-Einstiegspunkt.

Start: ``uvicorn app.main:app --reload`` oder ``make dev``.
"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api.schemas import HealthOut
from app.api import analyze as analyze_routes
from app.api import nvt as nvt_routes
from app.api import projects as project_routes
from app.api import uploads as upload_routes
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="VRA-NVT-Automation",
        version=__version__,
        description=(
            "Teil-automatisierte Erstellung technischer Unterlagen für "
            "verkehrsrechtliche Anordnungen bei Glasfaser-Einblasarbeiten an "
            "Netzverteilerschränken."
        ),
    )

    @app.get("/api/health", response_model=HealthOut, tags=["health"])
    def health() -> HealthOut:
        return HealthOut(
            status="ok",
            version=__version__,
            ruleset_version=settings.current_ruleset_version,
            vision_provider=settings.vision_provider,
            ocr_provider=settings.ocr_provider,
        )

    app.include_router(project_routes.router)
    app.include_router(upload_routes.router)
    app.include_router(nvt_routes.router)
    app.include_router(analyze_routes.router)

    return app


app = create_app()
