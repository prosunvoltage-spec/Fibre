"""Projekt-CRUD-Endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SettingsDep
from app.api.schemas import ProjectOut
from app.config import Settings
from app.core.repositories import ProjectRepo
from app.core.schemas import ProjectCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreateIn(ProjectCreate):
    """Wie ProjectCreate, aber ohne die von der API auto-gefüllten Felder."""

    ruleset_version: str | None = None  # type: ignore[assignment]
    vision_provider: str | None = None  # type: ignore[assignment]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateIn,
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> ProjectOut:
    repo = ProjectRepo(db)
    data = payload.model_dump(exclude_none=True)
    data.setdefault("ruleset_version", settings.current_ruleset_version)
    data.setdefault("vision_provider", settings.vision_provider)
    project = repo.create(ProjectCreate(**data))
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    limit: int = 100,
    offset: int = 0,
    db: Session = DbSession,
) -> list[ProjectOut]:
    return [ProjectOut.model_validate(p) for p in ProjectRepo(db).list(limit=limit, offset=offset)]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, db: Session = DbSession) -> ProjectOut:
    project = ProjectRepo(db).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, db: Session = DbSession) -> None:
    if not ProjectRepo(db).delete(project_id):
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
