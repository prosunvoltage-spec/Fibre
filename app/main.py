"""FastAPI-App: Zusammenschraubung von Routen, Middleware und Lifespan.

Minimales Setup für Phase 4 — Projekt-CRUD und Uploads. Weitere Routen
(Review, Rule Engine, Export) folgen in späteren Phasen.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.projects import router as projects_router
from app.api.uploads import router as uploads_router
from app.core.db import Base, get_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=get_engine())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="VRA-NVT-Automation",
        description=(
            "Teil-automatisierte Erstellung technischer Unterlagen für "
            "verkehrsrechtliche Anordnungen (VRA) bei Glasfaser-Einblasarbeiten."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(projects_router)
    app.include_router(uploads_router)
    return app


app = create_app()
