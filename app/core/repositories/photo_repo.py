"""CRUD-Repository für Photos."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PhotoKind
from app.core.models import Photo
from app.core.schemas import PhotoCreate


class PhotoRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: PhotoCreate) -> Photo:
        photo = Photo(
            nvt_id=data.nvt_id,
            filename=data.filename,
            stored_path=data.stored_path,
            mime_type=data.mime_type,
            width=data.width,
            height=data.height,
            sha256=data.sha256,
            exif=dict(data.exif),
            ocr_json=data.ocr_json,
            kind=data.kind,
        )
        self.session.add(photo)
        self.session.flush()
        return photo

    def get(self, photo_id: UUID) -> Photo | None:
        return self.session.get(Photo, photo_id)

    def find_by_sha256(
        self,
        sha256: str,
        *,
        nvt_id: UUID | None = None,
    ) -> Photo | None:
        stmt = select(Photo).where(Photo.sha256 == sha256)
        if nvt_id is not None:
            stmt = stmt.where(Photo.nvt_id == nvt_id)
        return self.session.scalars(stmt).first()

    def list_by_nvt(
        self, nvt_id: UUID, *, kind: PhotoKind | None = None
    ) -> list[Photo]:
        stmt = select(Photo).where(Photo.nvt_id == nvt_id)
        if kind is not None:
            stmt = stmt.where(Photo.kind == kind)
        stmt = stmt.order_by(Photo.created_at)
        return list(self.session.scalars(stmt))

    def known_sha256_for_project(self, project_id: UUID) -> set[str]:
        """Alle bereits gespeicherten SHA-256-Hashes eines Projekts."""
        from app.core.models import Nvt

        stmt = (
            select(Photo.sha256)
            .join(Nvt, Photo.nvt_id == Nvt.id)
            .where(Nvt.project_id == project_id)
        )
        return set(self.session.scalars(stmt))

    def update_ocr(self, photo: Photo, ocr_json: dict) -> Photo:
        photo.ocr_json = ocr_json
        self.session.flush()
        return photo
