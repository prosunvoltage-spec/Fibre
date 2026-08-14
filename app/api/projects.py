"""Projekt-CRUD — minimales Set, damit Uploads gegen ein Projekt laufen können."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.repositories import ProjectRepo
from app.core.schemas import ProjectCreate, ProjectSchema

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)) -> ProjectSchema:
    project = ProjectRepo(db).create(data)
    return ProjectSchema.model_validate(project, from_attributes=True)


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(project_id: UUID, db: Session = Depends(get_db)) -> ProjectSchema:
    project = ProjectRepo(db).get(project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Projekt {project_id} unbekannt")
    return ProjectSchema.model_validate(project, from_attributes=True)


@router.get("", response_model=list[ProjectSchema])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectSchema]:
    projects = ProjectRepo(db).list()
    return [ProjectSchema.model_validate(p, from_attributes=True) for p in projects]
