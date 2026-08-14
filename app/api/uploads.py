"""Upload-Endpoint für Foto-ZIPs bzw. einzelne JPGs."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ocr_provider
from app.classification import detect_nvt
from app.config import get_settings
from app.core.repositories import PhotoRepo, ProjectRepo
from app.core.services import IngestSummary, ingest_and_group
from app.ocr import OCRProvider
from app.uploads import (
    IngestedPhoto,
    IngestError,
    ingest_bytes_as_zip,
    ingest_files,
)

router = APIRouter(prefix="/api/projects/{project_id}/uploads", tags=["uploads"])


class PerNvtResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nvt_id: UUID
    nvt_number: str
    created: bool
    photos_created: int
    photos_skipped_duplicate: int
    warnings: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    ingested_files: int
    per_nvt: list[PerNvtResponse]
    unassigned_photo_sha256: list[str] = Field(default_factory=list)
    unassigned_warnings: list[str] = Field(default_factory=list)


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_photos(
    project_id: UUID,
    files: list[UploadFile] = File(..., description="ZIP-Dateien oder JPGs"),
    nvt_overrides: str | None = Form(
        default=None,
        description='JSON: {"NVT_7101.jpg": "7101"} — Zuordnung Dateiname → NVT-Nr',
    ),
    db: Session = Depends(get_db),
    ocr_provider: OCRProvider = Depends(get_ocr_provider),
) -> UploadResponse:
    # Projekt-Existenz prüfen
    if ProjectRepo(db).get(project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Projekt {project_id} unbekannt")

    overrides = _parse_overrides(nvt_overrides)
    storage_root = get_settings().storage_path
    known_sha256 = PhotoRepo(db).known_sha256_for_project(project_id)

    ingested: list[IngestedPhoto] = []
    ingested_count = 0
    for upload in files:
        blob = upload.file.read()
        ingested_count += 1
        try:
            if _looks_like_zip(upload, blob):
                ingested.extend(
                    ingest_bytes_as_zip(
                        blob,
                        project_id=project_id,
                        storage_root=storage_root,
                        known_sha256=known_sha256,
                    )
                )
            else:
                ingested.extend(
                    ingest_files(
                        [(upload.filename or "upload.jpg", blob)],
                        project_id=project_id,
                        storage_root=storage_root,
                        known_sha256=known_sha256,
                    )
                )
        except IngestError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        # sha256 sofort sperren, damit weitere ZIPs im selben Request nicht doppelt landen
        known_sha256.update(p.sha256 for p in ingested)

    assignments = []
    for photo in ingested:
        with photo.stored_path.open("rb") as fh:
            image_bytes = fh.read()
        ocr = ocr_provider.ocr_photo(image_bytes)
        override_key = photo.original_filename
        override_val = overrides.get(override_key) or overrides.get(photo.relative_path)
        assignments.append(detect_nvt(photo, ocr, user_override=override_val))

    summary: IngestSummary = ingest_and_group(db, project_id, assignments)

    return UploadResponse(
        project_id=project_id,
        ingested_files=ingested_count,
        per_nvt=[
            PerNvtResponse(
                nvt_id=p.nvt_id,
                nvt_number=p.nvt_number,
                created=p.created,
                photos_created=p.photos_created,
                photos_skipped_duplicate=p.photos_skipped_duplicate,
                warnings=p.warnings,
            )
            for p in summary.per_nvt
        ],
        unassigned_photo_sha256=summary.unassigned_photo_sha256,
        unassigned_warnings=summary.unassigned_warnings,
    )


def _parse_overrides(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"nvt_overrides ist kein gültiges JSON: {exc}",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "nvt_overrides muss ein Objekt {dateiname: nvt_nr} sein",
        )
    return {str(k): str(v) for k, v in data.items()}


def _looks_like_zip(upload: UploadFile, blob: bytes) -> bool:
    if upload.filename and upload.filename.lower().endswith(".zip"):
        return True
    if upload.content_type in ("application/zip", "application/x-zip-compressed"):
        return True
    return blob[:4] == b"PK\x03\x04" or blob[:4] == b"PK\x05\x06"
