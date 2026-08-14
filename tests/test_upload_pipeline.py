"""Integrations-Tests für Unpack + Photo-Processor + UploadService."""

from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from app.core.enums import NvtStatus
from app.core.models import Photo, Project
from app.core.repositories import NvtRepo, ProjectRepo
from app.core.schemas import ProjectCreate
from app.core.services import UploadService
from app.ocr import OCRResult
from app.uploads import unpack_upload


class FakeOCRProvider:
    """Deterministischer OCR-Provider für Tests."""

    id = "fake-ocr"

    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses

    def ocr_photo(self, photo_path):  # type: ignore[no-untyped-def]
        text = self.responses.get(photo_path.name, "")
        return OCRResult(text=text, confidence=0.9 if text else 0.0, provider=self.id)


def _make_jpg(path: Path, size: tuple[int, int] = (16, 16), color: str = "red") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path, "JPEG")


def _make_project(session: Session) -> Project:
    return ProjectRepo(session).create(
        ProjectCreate(
            name="Testprojekt",
            contractor="Firma",
            ruleset_version="v1",
            vision_provider="anthropic",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
        )
    )


# ---- Unpack ---------------------------------------------------------------


def test_unpack_directory(tmp_path: Path) -> None:
    src = tmp_path / "photos"
    _make_jpg(src / "NVT_7107.jpg")
    _make_jpg(src / "NVT_7108.jpg")
    _make_jpg(src / "README.txt".replace(".txt", ".jpg"))  # nur JPG
    result = unpack_upload(src, tmp_path / "work")
    assert result.count == 3


def test_unpack_zip(tmp_path: Path) -> None:
    _make_jpg(tmp_path / "a.jpg")
    _make_jpg(tmp_path / "b.jpg")
    zip_path = tmp_path / "u.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(tmp_path / "a.jpg", "NVT_7107.jpg")
        zf.write(tmp_path / "b.jpg", "NVT_7108.jpg")
    result = unpack_upload(zip_path, tmp_path / "work")
    assert result.count == 2


def test_unpack_zip_slip_rejected(tmp_path: Path) -> None:
    _make_jpg(tmp_path / "a.jpg")
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(tmp_path / "a.jpg", "../evil.jpg")
    result = unpack_upload(zip_path, tmp_path / "work")
    assert result.count == 0
    assert any("unsicherer Pfad" in reason for _, reason in result.skipped)


# ---- Upload-Service (End-to-End) -----------------------------------------


def test_flat_layout_creates_nvts_and_photos(session: Session, tmp_path: Path) -> None:
    project = _make_project(session)

    photos_dir = tmp_path / "photos"
    _make_jpg(photos_dir / "NVT_7107.jpg", color="red")
    _make_jpg(photos_dir / "NVT_7108.jpg", color="blue")

    unpacked = unpack_upload(photos_dir, tmp_path / "work")
    service = UploadService(session, ocr_provider=None, run_ocr=False)
    summary = service.process(project, unpacked, tmp_path / "input")

    assert summary.total_photos == 2
    assert summary.new_nvts == 2
    assert summary.duplicates == 0

    nvts = NvtRepo(session).list_for_project(project.id)
    assert {n.nvt_number for n in nvts} == {"7107", "7108"}
    assert all(NvtStatus(n.status) == NvtStatus.NEW for n in nvts)
    assert all(len(n.photos) == 1 for n in nvts)


def test_nested_layout_multi_photo_per_nvt(session: Session, tmp_path: Path) -> None:
    project = _make_project(session)

    photos_dir = tmp_path / "photos"
    _make_jpg(photos_dir / "NVT_7107" / "front.jpg", color="red")
    _make_jpg(photos_dir / "NVT_7107" / "side.jpg", color="green")
    _make_jpg(photos_dir / "NVT_7108" / "01.jpg", color="blue")

    unpacked = unpack_upload(photos_dir, tmp_path / "work")
    service = UploadService(session, ocr_provider=None, run_ocr=False)
    summary = service.process(project, unpacked, tmp_path / "input")

    assert summary.total_photos == 3
    assert summary.new_nvts == 2
    assert summary.updated_nvts == 1  # das zweite 7107-Foto

    nvt = NvtRepo(session).find_by_number(project.id, "7107")
    assert nvt is not None
    assert len(nvt.photos) == 2


def test_duplicate_photo_by_hash_is_skipped(session: Session, tmp_path: Path) -> None:
    project = _make_project(session)

    photos_dir = tmp_path / "photos"
    _make_jpg(photos_dir / "NVT_7107.jpg", color="red")
    # 2. Datei mit anderem Namen, aber gleichem Inhalt (gleiche Farbe & Größe)
    _make_jpg(photos_dir / "NVT_7107_copy.jpg", color="red")

    unpacked = unpack_upload(photos_dir, tmp_path / "work")
    service = UploadService(session, ocr_provider=None, run_ocr=False)
    summary = service.process(project, unpacked, tmp_path / "input")

    assert summary.total_photos == 2
    assert summary.duplicates == 1
    assert summary.new_nvts == 1
    photos = session.query(Photo).all()
    assert len(photos) == 1


def test_ocr_extracts_address(session: Session, tmp_path: Path) -> None:
    project = _make_project(session)

    photos_dir = tmp_path / "photos"
    _make_jpg(photos_dir / "NVT_7107.jpg")

    fake = FakeOCRProvider(
        {"NVT_7107.jpg": "Roxeler Straße 579\n48161 Münster\n19.02.2026 14:59"}
    )
    unpacked = unpack_upload(photos_dir, tmp_path / "work")
    service = UploadService(session, ocr_provider=fake, run_ocr=True)
    summary = service.process(project, unpacked, tmp_path / "input")

    assert summary.processed == 1
    nvt = NvtRepo(session).find_by_number(project.id, "7107")
    assert nvt is not None
    assert nvt.address_json is not None
    assert nvt.address_json["street"] == "Roxeler Straße"
    assert nvt.address_json["house_number"] == "579"
    assert nvt.address_json["postal_code"] == "48161"
    assert nvt.address_json["city"] == "Münster"


def test_manual_review_when_multiple_nvt_in_ocr(session: Session, tmp_path: Path) -> None:
    project = _make_project(session)

    photos_dir = tmp_path / "photos"
    _make_jpg(photos_dir / "foto.jpg")  # kein NVT im Dateinamen

    fake = FakeOCRProvider({"foto.jpg": "NVT 7107 und NVT 7108 im Bild"})
    unpacked = unpack_upload(photos_dir, tmp_path / "work")
    service = UploadService(session, ocr_provider=fake, run_ocr=True)
    summary = service.process(project, unpacked, tmp_path / "input")

    assert summary.manual_review_photos == 1
    assert summary.new_nvts == 0


def test_user_override_wins_over_filename(session: Session, tmp_path: Path) -> None:
    project = _make_project(session)

    photos_dir = tmp_path / "photos"
    _make_jpg(photos_dir / "NVT_7107.jpg")

    unpacked = unpack_upload(photos_dir, tmp_path / "work")
    service = UploadService(session, ocr_provider=None, run_ocr=False)
    summary = service.process(
        project,
        unpacked,
        tmp_path / "input",
        user_overrides={"NVT_7107.jpg": "7999"},
    )

    assert summary.new_nvts == 1
    assert NvtRepo(session).find_by_number(project.id, "7999") is not None
    assert NvtRepo(session).find_by_number(project.id, "7107") is None
