"""NVT-Listing-Endpoints (Details / Photos folgen in Phase 7)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.api.schemas import NvtOut
from app.core.enums import NvtStatus
from app.core.repositories import NvtRepo, ProjectRepo

router = APIRouter(prefix="/api/projects/{project_id}/nvts", tags=["nvt"])


def _to_out(nvt) -> NvtOut:  # type: ignore[no-untyped-def]
    out = NvtOut.model_validate(nvt)
    out.photo_count = len(nvt.photos)
    return out


@router.get("", response_model=list[NvtOut])
def list_nvts(
    project_id: UUID,
    status_filter: NvtStatus | None = Query(default=None, alias="status"),
    limit: int = 500,
    offset: int = 0,
    db: Session = DbSession,
) -> list[NvtOut]:
    if ProjectRepo(db).get(project_id) is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    nvts = NvtRepo(db).list_for_project(
        project_id, status=status_filter, limit=limit, offset=offset
    )
    return [_to_out(n) for n in nvts]


@router.get("/{nvt_id}", response_model=NvtOut)
def get_nvt(project_id: UUID, nvt_id: UUID, db: Session = DbSession) -> NvtOut:
    nvt = NvtRepo(db).get(nvt_id)
    if nvt is None or nvt.project_id != project_id:
        raise HTTPException(status_code=404, detail="NVT nicht gefunden")
    return _to_out(nvt)
