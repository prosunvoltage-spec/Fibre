"""Tests für ``app/core/services/nvt_service.py``."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.classification.nvt_detector import NvtAssignment, NvtIdSource
from app.core.models import Nvt, Photo, Project
from app.core.services import ingest_and_group
from app.ocr.parsers import ParsedOverlay
from app.uploads.ingest import IngestedPhoto


@pytest.fixture()
def project(session: Session) -> Project:
    p = Project(
        name="Testprojekt",
        contractor="Helder Santos GmbH",
        ruleset_version="v1",
        vision_provider="mock",
    )
    session.add(p)
    session.commit()
    return p


def _photo(*, sha: str, filename: str, tmp_path: Path) -> IngestedPhoto:
    stored = tmp_path / filename
    stored.write_bytes(b"x")
    return IngestedPhoto(
        original_filename=filename,
        relative_path=filename,
        stored_path=stored,
        mime_type="image/jpeg",
        width=100,
        height=100,
        sha256=sha,
    )


def _assignment(
    *,
    sha: str,
    filename: str,
    tmp_path: Path,
    nvt: str | None = "7101",
    overlay: ParsedOverlay | None = None,
    source: NvtIdSource = NvtIdSource.FILENAME,
    warnings: list[str] | None = None,
    manual: bool = False,
) -> NvtAssignment:
    return NvtAssignment(
        photo=_photo(sha=sha, filename=filename, tmp_path=tmp_path),
        nvt_number=nvt,
        source=source,
        parsed_overlay=overlay,
        warnings=warnings or [],
        manual_review_required=manual,
    )


def test_creates_nvt_and_photo(session: Session, project: Project, tmp_path: Path) -> None:
    overlay = ParsedOverlay(
        nvt_number="7101",
        street="Hauptstraße",
        house_number="12",
        postal_code="48159",
        city="Münster",
        gps_lat=Decimal("51.9"),
        gps_lon=Decimal("7.5"),
    )
    assign = _assignment(
        sha="a" * 64,
        filename="NVT_7101.jpg",
        tmp_path=tmp_path,
        overlay=overlay,
    )

    summary = ingest_and_group(session, project.id, [assign])
    session.commit()

    assert len(summary.per_nvt) == 1
    entry = summary.per_nvt[0]
    assert entry.nvt_number == "7101"
    assert entry.created is True
    assert entry.photos_created == 1
    assert entry.photos_skipped_duplicate == 0

    nvt = session.get(Nvt, entry.nvt_id)
    assert nvt is not None
    assert nvt.address_json is not None
    assert nvt.address_json["postal_code"] == "48159"
    assert nvt.location_json is not None
    assert Decimal(str(nvt.location_json["latitude"])) == Decimal("51.9")

    photos = session.query(Photo).filter(Photo.nvt_id == nvt.id).all()
    assert len(photos) == 1
    assert photos[0].sha256 == "a" * 64
    assert photos[0].ocr_json is not None


def test_groups_multiple_photos_into_one_nvt(
    session: Session, project: Project, tmp_path: Path
) -> None:
    a1 = _assignment(sha="a" * 64, filename="1.jpg", tmp_path=tmp_path)
    a2 = _assignment(sha="b" * 64, filename="2.jpg", tmp_path=tmp_path)
    summary = ingest_and_group(session, project.id, [a1, a2])
    session.commit()

    assert len(summary.per_nvt) == 1
    assert summary.per_nvt[0].photos_created == 2


def test_reuses_existing_nvt_and_dedupes_photos(
    session: Session, project: Project, tmp_path: Path
) -> None:
    a1 = _assignment(sha="a" * 64, filename="1.jpg", tmp_path=tmp_path)
    ingest_and_group(session, project.id, [a1])
    session.commit()

    # zweiter Upload: gleiche NVT, aber selbes sha256 -> Duplikat + ein neues Foto
    a1_again = _assignment(sha="a" * 64, filename="1_kopie.jpg", tmp_path=tmp_path)
    a2 = _assignment(sha="c" * 64, filename="2.jpg", tmp_path=tmp_path)
    summary = ingest_and_group(session, project.id, [a1_again, a2])
    session.commit()

    entry = summary.per_nvt[0]
    assert entry.created is False
    assert entry.photos_created == 1
    assert entry.photos_skipped_duplicate == 1


def test_unassigned_photos_reported_separately(
    session: Session, project: Project, tmp_path: Path
) -> None:
    unassigned = _assignment(
        sha="d" * 64,
        filename="mystery.jpg",
        tmp_path=tmp_path,
        nvt=None,
        source=NvtIdSource.NONE,
        warnings=["MANUELLE_PRUEFUNG_ERFORDERLICH: kein NVT-Hinweis"],
        manual=True,
    )
    good = _assignment(sha="e" * 64, filename="NVT_7102.jpg", tmp_path=tmp_path, nvt="7102")

    summary = ingest_and_group(session, project.id, [unassigned, good])
    session.commit()

    assert summary.unassigned_photo_sha256 == ["d" * 64]
    assert any("MANUELLE_PRUEFUNG" in w for w in summary.unassigned_warnings)
    assert len(summary.per_nvt) == 1


def test_enrich_missing_fields_does_not_overwrite(
    session: Session, project: Project, tmp_path: Path
) -> None:
    overlay1 = ParsedOverlay(
        nvt_number="7101",
        street="Alter Weg",
        house_number="1",
        postal_code="48000",
        city="Alt",
    )
    a1 = _assignment(sha="a" * 64, filename="1.jpg", tmp_path=tmp_path, overlay=overlay1)
    ingest_and_group(session, project.id, [a1])
    session.commit()

    overlay2 = ParsedOverlay(
        nvt_number="7101",
        street="Neuer Weg",
        house_number="99",
        postal_code="48999",
        city="Neu",
    )
    a2 = _assignment(sha="b" * 64, filename="2.jpg", tmp_path=tmp_path, overlay=overlay2)
    ingest_and_group(session, project.id, [a2])
    session.commit()

    nvt = session.query(Nvt).filter(Nvt.nvt_number == "7101").one()
    # Adresse aus erstem Upload bleibt erhalten
    assert nvt.address_json["city"] == "Alt"
    assert nvt.address_json["postal_code"] == "48000"


def test_warnings_accumulated_on_nvt(session: Session, project: Project, tmp_path: Path) -> None:
    a1 = _assignment(
        sha="a" * 64,
        filename="1.jpg",
        tmp_path=tmp_path,
        warnings=["Widerspruch A"],
    )
    a2 = _assignment(
        sha="b" * 64,
        filename="2.jpg",
        tmp_path=tmp_path,
        warnings=["Widerspruch B", "Widerspruch A"],  # A ist Duplikat
    )
    ingest_and_group(session, project.id, [a1, a2])
    session.commit()

    nvt = session.query(Nvt).filter(Nvt.nvt_number == "7101").one()
    assert set(nvt.warnings_json) == {"Widerspruch A", "Widerspruch B"}


def test_exif_gps_fallback_when_no_overlay_gps(
    session: Session, project: Project, tmp_path: Path
) -> None:
    photo = _photo(sha="a" * 64, filename="1.jpg", tmp_path=tmp_path)
    photo.exif_gps_lat = Decimal("51.5")
    photo.exif_gps_lon = Decimal("7.5")
    photo.exif_captured_at = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
    assign = NvtAssignment(
        photo=photo,
        nvt_number="7101",
        source=NvtIdSource.FILENAME,
        parsed_overlay=None,
        warnings=[],
    )
    ingest_and_group(session, project.id, [assign])
    session.commit()

    nvt = session.query(Nvt).filter(Nvt.nvt_number == "7101").one()
    assert nvt.location_json is not None
    assert Decimal(str(nvt.location_json["latitude"])) == Decimal("51.5")
    assert nvt.location_json["source"] == "exif"
