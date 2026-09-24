"""Visualize-Endpoint: erzeugt Overlay + gerendertes Proposal-Foto."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SettingsDep
from app.classification.visualization_builder import VisualizationBuilder
from app.config import Settings
from app.core.repositories import NvtRepo
from app.ruleplans import RulePlanLibrary

router = APIRouter(prefix="/api/projects/{project_id}/nvts/{nvt_id}/visualize", tags=["visualize"])


class VisualizeOut(BaseModel):
    nvt_id: str
    visualization_created: bool
    rendered_photo_path: str | None = None
    reason: str | None = None
    warnings: list[str] = []


@router.post("", response_model=VisualizeOut)
def visualize_nvt(
    project_id: UUID,
    nvt_id: UUID,
    force: bool = Query(default=False),
    user: str | None = Query(default=None),
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> VisualizeOut:
    nvt = NvtRepo(db).get(nvt_id)
    if nvt is None or nvt.project_id != project_id:
        raise HTTPException(status_code=404, detail="NVT nicht gefunden")

    library = RulePlanLibrary(settings.knowledge_path / "regelplaene").load()
    builder = VisualizationBuilder(
        db, library=library, storage_root=settings.storage_path, user=user,
    )
    outcome = builder.build_for_nvt(nvt, force=force)
    return VisualizeOut(
        nvt_id=outcome.nvt_id,
        visualization_created=outcome.visualization_created,
        rendered_photo_path=outcome.rendered_photo_path,
        reason=outcome.reason,
        warnings=outcome.warnings,
    )
