"""Upload-Endpoint: nimmt ZIP oder mehrere Dateien und ruft UploadService."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SettingsDep
from app.api.schemas import UploadPhotoOutcome, UploadSummaryOut
from app.config import Settings
from app.core.repositories import ProjectRepo
from app.core.services import UploadService
from app.ocr import TesseractOCRProvider
from app.uploads import UnpackError, unpack_upload

router = APIRouter(prefix="/api/projects/{project_id}/uploads", tags=["uploads"])

_MAX_FILE_BYTES = 100 * 1024 * 1024   # 100 MB pro Datei
_MAX_TOTAL_BYTES = 1024 * 1024 * 1024  # 1 GB pro Upload


@router.post(
    "",
    response_model=UploadSummaryOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photos(
    project_id: UUID,
    files: list[UploadFile] = File(..., description="ZIP oder Bilddateien"),
    user_overrides: str | None = Form(default=None, description="JSON dict {filename: nvt_number}"),
    run_ocr: bool = Form(default=True),
    user: str | None = Form(default=None),
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> UploadSummaryOut:
    project = ProjectRepo(db).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")

    overrides: dict[str, str] = {}
    if user_overrides:
        try:
            overrides = {str(k): str(v) for k, v in json.loads(user_overrides).items()}
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=422, detail=f"user_overrides ist kein gültiges JSON: {exc}"
            ) from exc

    # Uploads temporär spooln
    total = 0
    uploads_root = settings.storage_path / "uploads"
    uploads_root.mkdir(parents=True, exist_ok=True)
    stage_dir = Path(tempfile.mkdtemp(prefix="vra-upload-", dir=str(uploads_root)))
    try:
        for f in files:
            if not f.filename:
                continue
            content = await f.read()
            total += len(content)
            if len(content) > _MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Datei {f.filename} überschreitet Größenlimit ({_MAX_FILE_BYTES} bytes)",
                )
            if total > _MAX_TOTAL_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload überschreitet Gesamtlimit ({_MAX_TOTAL_BYTES} bytes)",
                )
            target = stage_dir / Path(f.filename).name
            target.write_bytes(content)

        # Entpacken
        work_dir = stage_dir / "_unpacked"
        source = _pick_upload_source(stage_dir, work_dir)
        try:
            unpacked = unpack_upload(source, work_dir)
        except UnpackError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        # Verarbeitung
        input_dir = settings.storage_path / "projects" / str(project.id) / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        ocr_provider = TesseractOCRProvider() if run_ocr else None
        service = UploadService(db, ocr_provider=ocr_provider, run_ocr=run_ocr)
        summary = service.process(
            project=project,
            unpacked=unpacked,
            input_dir=input_dir,
            user_overrides=overrides,
            user=user,
        )
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)

    return UploadSummaryOut(
        project_id=summary.project_id,
        total_photos=summary.total_photos,
        processed=summary.processed,
        skipped=summary.skipped,
        duplicates=summary.duplicates,
        new_nvts=summary.new_nvts,
        updated_nvts=summary.updated_nvts,
        manual_review_photos=summary.manual_review_photos,
        per_photo=[
            UploadPhotoOutcome(
                filename=p.filename,
                nvt_number=p.nvt_number,
                stored_path=str(p.stored_path) if p.stored_path else None,
                was_new_nvt=p.was_new_nvt,
                is_duplicate=p.duplicate_of_photo_id is not None,
                detection_source=(p.detection.source.value if p.detection and p.detection.source else None),
                warnings=p.warnings,
                error=p.error,
            )
            for p in summary.per_photo
        ],
    )


def _pick_upload_source(stage_dir: Path, work_dir: Path) -> Path:
    """Ein ZIP → ZIP-Pfad. Mehrere Dateien / ein Bild → Ordner."""
    entries = [p for p in stage_dir.iterdir() if p.is_file()]
    if len(entries) == 1 and entries[0].suffix.lower() == ".zip":
        return entries[0]
    return stage_dir
