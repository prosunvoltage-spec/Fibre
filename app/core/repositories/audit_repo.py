"""Append-only Audit-Log-Repository.

Das Repository unterstützt bewusst nur ``append`` und ``list``. Updates oder
Löschungen sind aus fachlichen Gründen (Nachvollziehbarkeit) nicht Teil der
API.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.models import AuditLog


class AuditRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(
        self,
        *,
        action: str,
        user: str | None = None,
        project_id: UUID | None = None,
        nvt_id: UUID | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        ruleset_version: str | None = None,
        model_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            user=user,
            project_id=project_id,
            nvt_id=nvt_id,
            old_value=old_value,
            new_value=new_value,
            ruleset_version=ruleset_version or get_settings().current_ruleset_version,
            model_id=model_id,
            payload=payload or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_for_nvt(self, nvt_id: UUID, limit: int = 100) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.nvt_id == nvt_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def list_for_project(self, project_id: UUID, limit: int = 500) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.project_id == project_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))
