"""API-spezifische Response-Schemas (nicht Domain-DTOs)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import NvtStatus


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectOut(_Out):
    id: UUID
    name: str
    location_label: str | None
    period_start: datetime | None
    period_end: datetime | None
    client: str | None
    contractor: str
    ruleset_version: str
    vision_provider: str
    created_at: datetime
    updated_at: datetime


class PhotoOut(_Out):
    id: UUID
    nvt_id: UUID
    filename: str
    stored_path: str
    mime_type: str
    width: int
    height: int
    sha256: str
    kind: str
    created_at: datetime


class NvtOut(_Out):
    id: UUID
    project_id: UUID
    nvt_number: str
    status: NvtStatus
    address_json: dict[str, Any] | None = None
    location_json: dict[str, Any] | None = None
    warnings_json: list[str] = []
    created_at: datetime
    updated_at: datetime
    photo_count: int = 0


class UploadPhotoOutcome(BaseModel):
    filename: str
    nvt_number: str | None
    stored_path: str | None
    was_new_nvt: bool = False
    is_duplicate: bool = False
    detection_source: str | None = None
    warnings: list[str] = []
    error: str | None = None


class UploadSummaryOut(BaseModel):
    project_id: UUID
    total_photos: int
    processed: int
    skipped: int
    duplicates: int
    new_nvts: int
    updated_nvts: int
    manual_review_photos: int
    per_photo: list[UploadPhotoOutcome] = []


class HealthOut(BaseModel):
    status: str
    version: str
    ruleset_version: str
    vision_provider: str
    ocr_provider: str
