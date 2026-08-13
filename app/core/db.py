"""Datenbank-Setup: Engine, Session, Basisklasse."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Deklarative Basis für alle ORM-Modelle."""


def _ensure_sqlite_path(url: str) -> None:
    """Bei SQLite: sicherstellen, dass Verzeichnis existiert."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return
    path_part = url[len(prefix):]
    if path_part in ("", ":memory:"):
        return
    Path(path_part).parent.mkdir(parents=True, exist_ok=True)


def create_engine_from_settings() -> Engine:
    """Baut das Engine-Objekt aus der aktuellen Konfiguration."""
    settings = get_settings()
    url = settings.database_url
    _ensure_sqlite_path(url)

    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        future=True,
        connect_args=connect_args,
        echo=False,
    )

    # SQLite: Foreign Keys aktivieren (per Default aus)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine_from_settings()
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session mit Transaktions-Rollback bei Fehlern."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_for_tests() -> None:
    """Für pytest-Fixtures: Engine/Sessionmaker neu aufbauen."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
