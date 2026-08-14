"""FastAPI-Dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.db import get_sessionmaker


def get_db() -> Iterator[Session]:
    """DB-Session pro Request (commit/rollback bei erfolg/fehler)."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def settings_dep() -> Settings:
    return get_settings()


DbSession = Depends(get_db)
SettingsDep = Depends(settings_dep)
