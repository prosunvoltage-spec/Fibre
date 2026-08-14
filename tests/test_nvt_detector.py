"""Tests für die NVT-Zuordnungs-Prioritätskette."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.classification.nvt_detector import NvtIdSource, detect_nvt
from app.ocr.base import OcrResult
from app.uploads.ingest import IngestedPhoto


def _photo(
    *,
    filename: str = "NVT_7101.jpg",
    folder_hint: str | None = None,
    filename_hint: str | None = None,
    tmp_path: Path,
) -> IngestedPhoto:
    stored = tmp_path / filename
    stored.write_bytes(b"x")
    return IngestedPhoto(
        original_filename=filename,
        relative_path=filename,
        stored_path=stored,
        mime_type="image/jpeg",
        width=100,
        height=100,
        sha256="a" * 64,
        folder_nvt_hint=folder_hint,
        filename_nvt_hint=filename_hint,
    )


def _ocr(text: str) -> OcrResult:
    return OcrResult(
        text=text,
        blocks=[],
        language="deu",
        provider="mock",
        provider_version="1",
        image_width=100,
        image_height=100,
    )


def test_user_override_wins(tmp_path: Path) -> None:
    photo = _photo(folder_hint="7101", filename_hint="7101", tmp_path=tmp_path)
    ocr = _ocr("NVT 7101")
    result = detect_nvt(photo, ocr, user_override="7999")
    assert result.nvt_number == "7999"
    assert result.source is NvtIdSource.USER


def test_user_override_warns_on_conflict(tmp_path: Path) -> None:
    photo = _photo(folder_hint="7101", tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7107"), user_override="7999")
    assert result.nvt_number == "7999"
    assert any("Ordner" in w and "7101" in w for w in result.warnings)
    assert any("OCR" in w and "7107" in w for w in result.warnings)


def test_folder_wins_over_filename_and_ocr(tmp_path: Path) -> None:
    photo = _photo(folder_hint="7101", filename_hint="7102", tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7103"))
    assert result.nvt_number == "7101"
    assert result.source is NvtIdSource.FOLDER
    assert any("Datei" in w for w in result.warnings)
    assert any("OCR" in w for w in result.warnings)


def test_filename_wins_over_ocr(tmp_path: Path) -> None:
    photo = _photo(filename_hint="7102", tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7103"))
    assert result.nvt_number == "7102"
    assert result.source is NvtIdSource.FILENAME
    assert any("OCR" in w and "7103" in w for w in result.warnings)


def test_ocr_used_when_no_hints(tmp_path: Path) -> None:
    photo = _photo(tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7107 Roxeler Straße 42"))
    assert result.nvt_number == "7107"
    assert result.source is NvtIdSource.OCR
    assert result.warnings == []


def test_multiple_ocr_numbers_without_hints_triggers_manual(tmp_path: Path) -> None:
    photo = _photo(tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7107 auch NVT 7108"))
    assert result.nvt_number is None
    assert result.source is NvtIdSource.NONE
    assert result.manual_review_required is True
    assert any("MANUELLE_PRUEFUNG" in w for w in result.warnings)


def test_no_hints_and_no_ocr_number(tmp_path: Path) -> None:
    photo = _photo(tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("random text"))
    assert result.nvt_number is None
    assert result.manual_review_required is True


def test_no_ocr_available(tmp_path: Path) -> None:
    photo = _photo(filename_hint="7107", tmp_path=tmp_path)
    result = detect_nvt(photo, None)
    assert result.nvt_number == "7107"
    assert result.source is NvtIdSource.FILENAME
    assert result.parsed_overlay is None


def test_ocr_agreement_no_warning(tmp_path: Path) -> None:
    photo = _photo(folder_hint="7101", tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7101 Foto"))
    assert result.nvt_number == "7101"
    assert result.source is NvtIdSource.FOLDER
    assert result.warnings == []


def test_parsed_overlay_carries_address(tmp_path: Path) -> None:
    photo = _photo(filename_hint="7101", tmp_path=tmp_path)
    result = detect_nvt(photo, _ocr("NVT 7101 Hauptstraße 12 48159 Münster"))
    assert result.parsed_overlay is not None
    assert result.parsed_overlay.street == "Hauptstraße"
    assert result.parsed_overlay.postal_code == "48159"


@pytest.mark.parametrize("hint,expected", [("7101", "7101"), ("7101 ", "7101"), ("nvt-7101", "NVT-7101")])
def test_normalize_uppercases_and_strips(tmp_path: Path, hint: str, expected: str) -> None:
    photo = _photo(tmp_path=tmp_path)
    result = detect_nvt(photo, None, user_override=hint)
    assert result.nvt_number == expected.upper().strip()


def test_gps_and_datetime_parsed(tmp_path: Path) -> None:
    photo = _photo(filename_hint="7107", tmp_path=tmp_path)
    ocr = _ocr("NVT 7107 GPS: 51.9, 7.5 - 13.08.2026 14:32")
    result = detect_nvt(photo, ocr)
    assert result.parsed_overlay is not None
    assert result.parsed_overlay.gps_lat == Decimal("51.9")
    assert result.parsed_overlay.captured_at is not None
