"""CRUD-Repository für NVT-Aggregate mit State-Machine-Guard."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import NvtStatus, is_valid_transition
from app.core.models import Nvt
from app.core.schemas import NvtCreate


class DuplicateNvtNumberError(ValueError):
    """Wird geworfen, wenn (project_id, nvt_number) bereits existiert."""


class InvalidStateTransition(ValueError):
    """Wird geworfen, wenn ein Statuswechsel nicht in NVT_STATUS_TRANSITIONS zulässig ist."""

    def __init__(self, current: NvtStatus, target: NvtStatus) -> None:
        super().__init__(
            f"Übergang {current.value} → {target.value} ist nicht zulässig"
        )
        self.current = current
        self.target = target


class NvtRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: NvtCreate) -> Nvt:
        nvt = Nvt(
            project_id=data.project_id,
            nvt_number=data.nvt_number,
            address_json=data.address.model_dump(mode="json") if data.address else None,
            location_json=data.location.model_dump(mode="json") if data.location else None,
            warnings_json=[],
        )
        self.session.add(nvt)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateNvtNumberError(
                f"NVT-Nummer '{data.nvt_number}' existiert bereits in diesem Projekt"
            ) from exc
        return nvt

    def get(self, nvt_id: UUID) -> Nvt | None:
        return self.session.get(Nvt, nvt_id)

    def find_by_number(self, project_id: UUID, nvt_number: str) -> Nvt | None:
        stmt = select(Nvt).where(
            Nvt.project_id == project_id, Nvt.nvt_number == nvt_number
        )
        return self.session.scalars(stmt).first()

    def list_for_project(
        self,
        project_id: UUID,
        status: NvtStatus | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Nvt]:
        stmt = select(Nvt).where(Nvt.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Nvt.status == status)
        stmt = stmt.order_by(Nvt.nvt_number).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def update_status(self, nvt: Nvt, new_status: NvtStatus) -> Nvt:
        """Statuswechsel mit Guard aus NVT_STATUS_TRANSITIONS."""
        current = NvtStatus(nvt.status) if isinstance(nvt.status, str) else nvt.status
        if not is_valid_transition(current, new_status):
            raise InvalidStateTransition(current, new_status)
        nvt.status = new_status
        self.session.flush()
        return nvt

    def add_warning(self, nvt: Nvt, warning: str) -> Nvt:
        warnings = list(nvt.warnings_json or [])
        if warning not in warnings:
            warnings.append(warning)
        nvt.warnings_json = warnings
        self.session.flush()
        return nvt

    def delete(self, nvt_id: UUID) -> bool:
        nvt = self.get(nvt_id)
        if nvt is None:
            return False
        self.session.delete(nvt)
        self.session.flush()
        return True
