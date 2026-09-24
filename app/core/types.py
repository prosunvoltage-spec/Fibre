"""Cross-Datenbank-Typen für SQLAlchemy.

SQLite hat kein natives UUID. Der ``GUID``-Typ speichert UUIDs als CHAR(36)
in SQLite bzw. UUID in PostgreSQL, und wandelt in Python immer in
``uuid.UUID`` um.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator[UUID]):
    """Plattformunabhängiger UUID-Typ."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value if dialect.name == "postgresql" else str(value)
        return value if dialect.name == "postgresql" else str(UUID(str(value)))

    def process_result_value(self, value: Any, dialect: Any) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        return UUID(str(value))
