"""Dependency-Injection für FastAPI-Routen."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.db import get_sessionmaker
from app.ocr import OCRProvider, build_default_ocr_provider


def get_db() -> Iterator[Session]:
    """Öffnet eine DB-Session pro Request und schließt sie garantiert."""
    session_local = get_sessionmaker()
    session = session_local()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_ocr_provider() -> OCRProvider:
    """Default-OCR-Provider gemäß ``Settings.ocr_provider``.

    Tests können diese Abhängigkeit mit ``app.dependency_overrides`` durch
    z.B. ``MockOCRProvider`` ersetzen.
    """
    return build_default_ocr_provider()
