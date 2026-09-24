"""Pytest-Fixtures: In-Memory-SQLite mit frisch angelegtem Schema pro Test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base

# Modelle importieren, damit Base.metadata gefüllt ist
import app.core.models  # noqa: F401


@pytest.fixture()
def engine() -> Iterator[Engine]:
    """Frische In-Memory-DB pro Test."""
    eng = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    """Session mit auto-Rollback am Testende."""
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()
