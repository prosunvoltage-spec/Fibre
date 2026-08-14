"""Export-Endpoints: QA-Gate, DOCX-Erzeugung, Auslieferung."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SettingsDep
from app.config import Settings
from app.core.repositories import ProjectRepo
from app.core.services import ExportService
from app.ruleplans import RulePlanLibrary

router = APIRouter(prefix="/api/projects/{project_id}/exports", tags=["exports"])


class ExportOut(BaseModel):
    project_id: str
    docx_path: str | None
    html_report_path: str | None
    passed: bool
    included_nvt_ids: list[str] = []
    warnings: list[str] = []
    qa_report: dict = {}
    superseded_export_ids: list[str] = []


@router.post("", response_model=ExportOut)
def create_export(
    project_id: UUID,
    dry_run: bool = Query(default=False),
    require_review: bool = Query(default=True),
    user: str | None = Query(default=None),
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> ExportOut:
    project = ProjectRepo(db).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")

    library = RulePlanLibrary(settings.knowledge_path / "regelplaene").load()
    service = ExportService(db, library=library, storage_root=settings.storage_path, user=user)
    summary = service.export_project(project, require_review=require_review, dry_run=dry_run)
    return ExportOut(**summary.__dict__)


@router.get("/latest.docx", response_class=FileResponse)
def download_latest_docx(
    project_id: UUID,
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> FileResponse:
    """Liefert die zuletzt generierte Word-Anlage."""
    from sqlalchemy import select

    from app.core.models import Export

    if ProjectRepo(db).get(project_id) is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    latest = db.scalar(
        select(Export)
        .where(Export.project_id == project_id, Export.superseded.is_(False))
        .order_by(Export.generated_at.desc())
    )
    if latest is None or not Path(latest.docx_path).is_file():
        raise HTTPException(status_code=404, detail="Kein Export vorhanden")
    return FileResponse(
        path=latest.docx_path,
        filename=Path(latest.docx_path).name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
