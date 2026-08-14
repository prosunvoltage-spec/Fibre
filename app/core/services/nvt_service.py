"""NVT-Service: Fotos einem NVT-Aggregat zuordnen und persistieren.

Nimmt eine Liste ``NvtAssignment`` (die kommt vom OCR- und Detector-Lauf
aus dem Upload-Endpoint) und legt daraus in der DB an:

* pro eindeutiger NVT-Nummer genau einen ``Nvt``-Record
  (bei bestehender Nummer im selben Projekt wird der bestehende Record
  wiederverwendet — Uploads sind additiv)
* pro Foto genau einen ``Photo``-Record; Duplikate (gleiches SHA-256)
  werden übersprungen
* Adresse/GPS werden aus dem ersten Foto der Gruppe befüllt, das die
  Werte liefert — bereits gespeicherte Werte werden nicht überschrieben
* Warnungen (Widersprüche, fehlende Zuordnungen) landen im
  ``warnings_json`` des jeweiligen NVT

Nicht zugewiesene Fotos (``NvtAssignment.nvt_number is None``) werden in
einem separaten Sammel-Bucket zurückgemeldet — kein DB-Eintrag, damit
der Reviewer sie manuell verteilen kann.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.classification.nvt_detector import NvtAssignment
from app.core.enums import AddressSource, LocationSource
from app.core.models import Nvt
from app.core.repositories import NvtRepo, PhotoRepo
from app.core.repositories.nvt_repo import DuplicateNvtNumberError
from app.core.schemas import AddressSchema, LocationSchema, NvtCreate, PhotoCreate


@dataclass(slots=True)
class IngestSummaryPerNvt:
    nvt_id: UUID
    nvt_number: str
    created: bool  # True = NVT-Record neu angelegt
    photos_created: int
    photos_skipped_duplicate: int
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IngestSummary:
    project_id: UUID
    per_nvt: list[IngestSummaryPerNvt] = field(default_factory=list)
    unassigned_photo_sha256: list[str] = field(default_factory=list)
    unassigned_warnings: list[str] = field(default_factory=list)

    @property
    def created_nvt_ids(self) -> list[UUID]:
        return [n.nvt_id for n in self.per_nvt if n.created]

    @property
    def total_photos_created(self) -> int:
        return sum(n.photos_created for n in self.per_nvt)


def ingest_and_group(
    session: Session,
    project_id: UUID,
    assignments: Sequence[NvtAssignment],
) -> IngestSummary:
    """Persistiert die Ergebnisse eines Upload-Laufs."""

    nvt_repo = NvtRepo(session)
    photo_repo = PhotoRepo(session)

    grouped: dict[str, list[NvtAssignment]] = {}
    summary = IngestSummary(project_id=project_id)

    for assignment in assignments:
        if assignment.nvt_number is None:
            summary.unassigned_photo_sha256.append(assignment.photo.sha256)
            for w in assignment.warnings:
                if w not in summary.unassigned_warnings:
                    summary.unassigned_warnings.append(w)
            continue
        grouped.setdefault(assignment.nvt_number, []).append(assignment)

    for nvt_number, group in grouped.items():
        per_nvt = _process_group(
            session=session,
            nvt_repo=nvt_repo,
            photo_repo=photo_repo,
            project_id=project_id,
            nvt_number=nvt_number,
            group=group,
        )
        summary.per_nvt.append(per_nvt)

    return summary


def _process_group(
    *,
    session: Session,
    nvt_repo: NvtRepo,
    photo_repo: PhotoRepo,
    project_id: UUID,
    nvt_number: str,
    group: list[NvtAssignment],
) -> IngestSummaryPerNvt:
    existing = nvt_repo.find_by_number(project_id, nvt_number)
    address, location = _pick_address_and_location(group)

    if existing is None:
        create = NvtCreate(
            project_id=project_id,
            nvt_number=nvt_number,
            address=address,
            location=location,
        )
        try:
            nvt = nvt_repo.create(create)
        except DuplicateNvtNumberError:  # Race — sicherheitshalber nochmal holen
            nvt = nvt_repo.find_by_number(project_id, nvt_number)
            assert nvt is not None
            created = False
        else:
            created = True
    else:
        nvt = existing
        created = False
        _enrich_missing_fields(nvt, address, location)

    warnings_collected: list[str] = []
    photos_created = 0
    photos_skipped = 0

    for assignment in group:
        photo = assignment.photo
        existing_photo = photo_repo.find_by_sha256(photo.sha256, nvt_id=nvt.id)
        if existing_photo is not None:
            photos_skipped += 1
        else:
            photo_repo.create(
                PhotoCreate(
                    nvt_id=nvt.id,
                    filename=photo.original_filename,
                    stored_path=str(photo.stored_path),
                    mime_type=photo.mime_type,
                    width=photo.width,
                    height=photo.height,
                    sha256=photo.sha256,
                    exif=dict(photo.exif),
                    ocr_json=(
                        assignment.parsed_overlay.model_dump(mode="json")
                        if assignment.parsed_overlay is not None
                        else None
                    ),
                )
            )
            photos_created += 1

        for w in assignment.warnings:
            if w not in warnings_collected:
                warnings_collected.append(w)

    for w in warnings_collected:
        nvt_repo.add_warning(nvt, w)

    session.flush()

    return IngestSummaryPerNvt(
        nvt_id=nvt.id,
        nvt_number=nvt_number,
        created=created,
        photos_created=photos_created,
        photos_skipped_duplicate=photos_skipped,
        warnings=warnings_collected,
    )


def _pick_address_and_location(
    group: list[NvtAssignment],
) -> tuple[AddressSchema | None, LocationSchema | None]:
    """Erste Adresse/GPS aus der Gruppe (OCR bevorzugt, EXIF-GPS als Fallback)."""

    address: AddressSchema | None = None
    location: LocationSchema | None = None

    for assignment in group:
        overlay = assignment.parsed_overlay
        if address is None and overlay and overlay.has_address:
            address = AddressSchema(
                street=overlay.street,
                house_number=overlay.house_number,
                postal_code=overlay.postal_code,
                city=overlay.city,
                raw=None,
                source=AddressSource.OCR,
            )
        if location is None and overlay and overlay.has_gps:
            location = LocationSchema(
                latitude=overlay.gps_lat,
                longitude=overlay.gps_lon,
                source=LocationSource.OCR,
            )
        if location is None and assignment.photo.exif_gps_lat is not None:
            location = LocationSchema(
                latitude=assignment.photo.exif_gps_lat,
                longitude=assignment.photo.exif_gps_lon,
                source=LocationSource.EXIF,
            )
        if address is not None and location is not None:
            break

    return address, location


def _enrich_missing_fields(
    nvt: Nvt,
    address: AddressSchema | None,
    location: LocationSchema | None,
) -> None:
    """Nur füllen, was noch nicht da ist. Keine Überschreibung."""
    if address is not None and not nvt.address_json:
        nvt.address_json = address.model_dump(mode="json")
    if location is not None and not nvt.location_json:
        nvt.location_json = location.model_dump(mode="json")
    nvt.updated_at = datetime.now(UTC)
