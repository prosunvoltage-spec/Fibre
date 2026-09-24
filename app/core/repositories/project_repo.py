"""CRUD-Repository für Projekte."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Project
from app.core.schemas import ProjectCreate


class ProjectRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump())
        self.session.add(project)
        self.session.flush()
        return project

    def get(self, project_id: UUID) -> Project | None:
        return self.session.get(Project, project_id)

    def list(self, limit: int = 100, offset: int = 0) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def delete(self, project_id: UUID) -> bool:
        project = self.get(project_id)
        if project is None:
            return False
        self.session.delete(project)
        self.session.flush()
        return True
