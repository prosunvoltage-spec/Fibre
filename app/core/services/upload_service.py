"""Orchestriert Upload → Entpacken → OCR → NVT-Erkennung → DB.

Hier liegt die Anwendungslogik zwischen den technischen Adaptern
(``app/uploads/``, ``app/ocr/``, ``app/classification/``) und den
Repositories (``app/core/repositories/``).

Der Service ist bewusst synchron: er läuft im Job-Worker (Phase 10) und
soll transaktional (all-or-nothing pro Upload) sein.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.classification import NvtDetection, detect_nvt_number
from app.core.enums import PhotoKind
from app.core.models import Nvt, Photo, Project
from app.core.repositories import AuditRepo, NvtRepo
from app.core.schemas import AddressSchema, LocationSchema, NvtCreate
from app.ocr import ExtractedText, OCRProvider, extract_structured
from app.uploads import UnpackedUpload, process_photo

logger = logging.getLogger(__name__)


@dataclass
class PhotoOutcome:
    filename: str
    stored_path: Path | None
    nvt_number: str | None
    detection: NvtDetection | None
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    duplicate_of_photo_id: str | None = None
    was_new_nvt: bool = False


@dataclass
class UploadSummary:
    project_id: UUID
    total_photos: int
    processed: int
    skipped: int
    duplicates: int
    new_nvts: int
    updated_nvts: int
    manual_review_photos: int
    per_photo: list[PhotoOutcome] = field(default_factory=list)

    def has_warnings(self) -> bool:
        return any(p.warnings for p in self.per_photo)


class UploadService:
    """Verarbeitet einen entpackten Upload für ein Projekt.

    Der Aufrufer entscheidet, ob und wie OCR läuft (Provider-Injection).
    Beim ersten Upload eines NVT wird ein neuer Datensatz angelegt; weitere
    Fotos werden zum bestehenden NVT hinzugefügt (Multi-Foto pro NVT).
    """

    def __init__(
        self,
        session: Session,
        *,
        ocr_provider: OCRProvider | None = None,
        run_ocr: bool = True,
    ) -> None:
        self.session = session
        self.ocr_provider = ocr_provider
        self.run_ocr = run_ocr and ocr_provider is not None
        self._nvt_repo = NvtRepo(session)
        self._audit = AuditRepo(session)

    def process(
        self,
        project: Project,
        unpacked: UnpackedUpload,
        input_dir: Path,
        user_overrides: dict[str, str] | None = None,
        user: str | None = None,
    ) -> UploadSummary:
        """Verarbeitet alle Fotos aus ``unpacked``.

        - ``input_dir`` ist der Zielordner für Kopien (typischerweise
          ``data/projects/{pid}/input``).
        - ``user_overrides`` erlaubt explizite NVT-Zuordnung pro Dateiname.
        """
        overrides = user_overrides or {}
        summary = UploadSummary(
            project_id=project.id,
            total_photos=len(unpacked.photos),
            processed=0,
            skipped=0,
            duplicates=0,
            new_nvts=0,
            updated_nvts=0,
            manual_review_photos=0,
        )

        for raw_path in unpacked.photos:
            rel_dir = self._relative_dir(raw_path, unpacked.root)
            outcome = self._process_single(
                project=project,
                raw_path=raw_path,
                input_dir=input_dir,
                relative_dir=rel_dir,
                user_override=overrides.get(raw_path.name),
                user=user,
            )
            summary.per_photo.append(outcome)
            if outcome.error:
                summary.skipped += 1
            else:
                summary.processed += 1
                if outcome.duplicate_of_photo_id:
                    summary.duplicates += 1
                if outcome.was_new_nvt:
                    summary.new_nvts += 1
                elif outcome.nvt_number:
                    summary.updated_nvts += 1
            if outcome.detection and outcome.detection.needs_manual_review():
                summary.manual_review_photos += 1

        self._audit.append(
            action="UPLOAD_PROCESSED",
            user=user,
            project_id=project.id,
            new_value=str(summary.processed),
            payload={
                "total": summary.total_photos,
                "processed": summary.processed,
                "duplicates": summary.duplicates,
                "new_nvts": summary.new_nvts,
                "manual_review_photos": summary.manual_review_photos,
            },
        )
        return summary

    # ------------------------------------------------------------------
    # Intern
    # ------------------------------------------------------------------

    def _relative_dir(self, raw_path: Path, root: Path) -> str:
        try:
            rel = raw_path.relative_to(root)
        except ValueError:
            return ""
        parent = rel.parent
        return "" if parent == Path(".") else str(parent)

    def _process_single(
        self,
        *,
        project: Project,
        raw_path: Path,
        input_dir: Path,
        relative_dir: str,
        user_override: str | None,
        user: str | None,
    ) -> PhotoOutcome:
        outcome = PhotoOutcome(filename=raw_path.name, stored_path=None, nvt_number=None, detection=None)

        # 1. Foto verarbeiten (kopieren, EXIF, Hash)
        try:
            info = process_photo(raw_path, input_dir, relative_group=relative_dir or None)
        except Exception as exc:  # pragma: no cover — defensive
            outcome.error = f"Foto-Verarbeitung fehlgeschlagen: {exc}"
            logger.exception("Foto-Verarbeitung fehlgeschlagen für %s", raw_path)
            return outcome

        outcome.stored_path = info.stored_path

        # 2. OCR (optional)
        ocr_text = ""
        ocr_json: dict[str, object] | None = None
        extracted: ExtractedText | None = None
        if self.run_ocr and self.ocr_provider is not None:
            ocr_result = self.ocr_provider.ocr_photo(raw_path)
            ocr_text = ocr_result.text
            outcome.ocr_used = True
            extracted = extract_structured(ocr_text)
            ocr_json = {
                "provider": ocr_result.provider,
                "confidence": ocr_result.confidence,
                "text": ocr_text,
                "structured": extracted.to_dict(),
                "warnings": ocr_result.warnings,
            }
            outcome.warnings.extend(ocr_result.warnings)

        # 3. NVT-Erkennung
        detection = detect_nvt_number(
            filename=raw_path.name,
            relative_dir=relative_dir,
            ocr_text=ocr_text,
            user_override=user_override,
        )
        outcome.detection = detection
        outcome.warnings.extend(detection.warnings)

        if detection.nvt_number is None:
            outcome.warnings.append(
                "Foto wird gespeichert, aber keinem NVT zugeordnet — manuelle Prüfung nötig"
            )
            return outcome

        outcome.nvt_number = detection.nvt_number

        # 4. NVT-Datensatz finden oder anlegen
        nvt = self._nvt_repo.find_by_number(project.id, detection.nvt_number)
        was_new_nvt = False
        if nvt is None:
            nvt = self._nvt_repo.create(
                NvtCreate(
                    project_id=project.id,
                    nvt_number=detection.nvt_number,
                    address=self._build_address(extracted),
                    location=self._build_location(info, extracted),
                )
            )
            was_new_nvt = True
            outcome.was_new_nvt = True
            self._audit.append(
                action="NVT_CREATED",
                user=user,
                project_id=project.id,
                nvt_id=nvt.id,
                new_value=detection.nvt_number,
                payload={"source": detection.source.value if detection.source else None},
            )
        else:
            self._maybe_enrich_nvt(nvt, info, extracted)

        # 5. Duplikat-Check + Photo-Datensatz
        duplicate = self._find_duplicate_photo(nvt, info.sha256)
        if duplicate:
            outcome.duplicate_of_photo_id = str(duplicate.id)
            outcome.warnings.append(
                f"Duplikat: SHA256 bereits als Foto {duplicate.id} vorhanden"
            )
            self._audit.append(
                action="PHOTO_DUPLICATE",
                user=user,
                project_id=project.id,
                nvt_id=nvt.id,
                payload={"sha256": info.sha256, "existing_photo_id": str(duplicate.id)},
            )
            return outcome

        photo = Photo(
            nvt_id=nvt.id,
            filename=info.original_filename,
            stored_path=str(info.stored_path),
            mime_type=info.mime_type,
            width=info.width,
            height=info.height,
            sha256=info.sha256,
            exif=info.exif,
            ocr_json=ocr_json,
            kind=PhotoKind.ORIGINAL,
        )
        self.session.add(photo)
        self.session.flush()

        self._audit.append(
            action="PHOTO_INGESTED",
            user=user,
            project_id=project.id,
            nvt_id=nvt.id,
            payload={
                "photo_id": str(photo.id),
                "filename": info.original_filename,
                "sha256": info.sha256,
                "detection_source": detection.source.value if detection.source else None,
                "was_new_nvt": was_new_nvt,
            },
        )
        return outcome

    def _find_duplicate_photo(self, nvt: Nvt, sha: str) -> Photo | None:
        for existing in nvt.photos:
            if existing.sha256 == sha:
                return existing
        return None

    def _build_address(self, extracted: ExtractedText | None) -> AddressSchema | None:
        if extracted is None:
            return None
        if not any([extracted.street, extracted.house_number, extracted.postal_code, extracted.city]):
            return None
        from app.core.enums import AddressSource

        return AddressSchema(
            street=extracted.street,
            house_number=extracted.house_number,
            postal_code=extracted.postal_code,
            city=extracted.city,
            source=AddressSource.OCR,
        )

    def _build_location(self, info, extracted: ExtractedText | None) -> LocationSchema | None:
        from app.core.enums import LocationSource
        from decimal import Decimal

        lat = info.gps_latitude
        lon = info.gps_longitude
        source: LocationSource | None = LocationSource.EXIF if (lat and lon) else None

        if (lat is None or lon is None) and extracted and extracted.latitude and extracted.longitude:
            lat, lon = extracted.latitude, extracted.longitude
            source = LocationSource.OCR

        if lat is None or lon is None:
            return None
        return LocationSchema(
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lon)),
            source=source,
        )

    def _maybe_enrich_nvt(self, nvt: Nvt, info, extracted: ExtractedText | None) -> None:
        """Ergänzt fehlende Adresse/GPS, wenn ein späteres Foto sie liefert."""
        addr = self._build_address(extracted)
        if addr and not nvt.address_json:
            nvt.address_json = addr.model_dump(mode="json")
        loc = self._build_location(info, extracted)
        if loc and not nvt.location_json:
            nvt.location_json = loc.model_dump(mode="json")
