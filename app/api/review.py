"""Review-Endpoint: Freigabe/Ablehnung eines NVT durch einen Menschen.

Schreibt eine Review-Row (Audit-Trail) und treibt den Status entlang des
in NVT_STATUS_TRANSITIONS erlaubten Pfads. Freigabe geht immer über
REVIEWED -> APPROVED (nie direkt), Ablehnung ist von NEEDS_REVIEW/REVIEWED
aus jederzeit möglich.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.core.enums import NvtStatus, ReviewAction
from app.core.models import Review
from app.core.repositories import AuditRepo, InvalidStateTransition, NvtRepo

router = APIRouter(prefix="/api/projects/{project_id}/nvts/{nvt_id}/review", tags=["review"])


class ReviewIn(BaseModel):
    action: ReviewAction
    reviewer: str = Field(min_length=1)
    comment: str | None = None


class ReviewOut(BaseModel):
    nvt_id: str
    status: str
    action: str
    reviewer: str


@router.post("", response_model=ReviewOut)
def review_nvt(
    project_id: UUID,
    nvt_id: UUID,
    payload: ReviewIn,
    db: Session = DbSession,
) -> ReviewOut:
    nvt_repo = NvtRepo(db)
    nvt = nvt_repo.get(nvt_id)
    if nvt is None or nvt.project_id != project_id:
        raise HTTPException(status_code=404, detail="NVT nicht gefunden")

    current = NvtStatus(nvt.status)

    if payload.action == ReviewAction.APPROVED:
        if nvt.decision is None:
            raise HTTPException(
                status_code=400,
                detail="Keine Decision vorhanden — Rule Engine muss zuerst laufen",
            )
        try:
            if current == NvtStatus.NEEDS_REVIEW:
                nvt_repo.update_status(nvt, NvtStatus.REVIEWED)
                current = NvtStatus.REVIEWED
            nvt_repo.update_status(nvt, NvtStatus.APPROVED)
        except InvalidStateTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    elif payload.action == ReviewAction.REJECTED:
        try:
            nvt_repo.update_status(nvt, NvtStatus.REJECTED)
        except InvalidStateTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Andere ReviewAction-Werte (RULEPLAN_CHANGED, ENVIRONMENT_EDITED, ...)
    # protokollieren nur, ohne Statuswechsel — Bearbeitung selbst folgt in Phase 7.

    review = Review(
        nvt_id=nvt.id,
        reviewer=payload.reviewer,
        action=payload.action,
        comment=payload.comment,
        before={"status": current.value},
        after={"status": NvtStatus(nvt.status).value},
        timestamp=datetime.now(UTC),
    )
    db.add(review)
    db.flush()

    AuditRepo(db).append(
        action=payload.action.value,
        user=payload.reviewer,
        project_id=nvt.project_id,
        nvt_id=nvt.id,
        new_value=NvtStatus(nvt.status).value,
        payload={"comment": payload.comment},
    )

    return ReviewOut(
        nvt_id=str(nvt.id),
        status=NvtStatus(nvt.status).value,
        action=payload.action.value,
        reviewer=payload.reviewer,
    )
