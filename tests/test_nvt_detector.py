"""Tests für die NVT-Erkennung mit Prioritätskette."""

from __future__ import annotations

from app.classification import detect_nvt_number
from app.classification.nvt_detector import NvtDetectionSource


def test_user_override_wins() -> None:
    d = detect_nvt_number(
        filename="foto1.jpg",
        relative_dir="NVT_7999",
        ocr_text="NVT 7107",
        user_override="7500",
    )
    assert d.nvt_number == "7500"
    assert d.source == NvtDetectionSource.USER


def test_filename_beats_ocr() -> None:
    d = detect_nvt_number(filename="NVT_7107.jpg", ocr_text="NVT 7200")
    assert d.nvt_number == "7107"
    assert d.source == NvtDetectionSource.FILENAME
    # 7200 wird als Konflikt-Warnung erwähnt
    assert any("Mehrere NVT-Nummern erkannt" in w for w in d.warnings)


def test_folder_when_no_filename() -> None:
    d = detect_nvt_number(filename="01.jpg", relative_dir="NVT_7107")
    assert d.nvt_number == "7107"
    assert d.source == NvtDetectionSource.FOLDER


def test_ocr_only_single() -> None:
    d = detect_nvt_number(filename="foto.jpg", ocr_text="NVT 7107")
    assert d.nvt_number == "7107"
    assert d.source == NvtDetectionSource.OCR


def test_multiple_ocr_needs_review() -> None:
    d = detect_nvt_number(filename="foto.jpg", ocr_text="NVT 7107 und NVT 7108")
    assert d.nvt_number is None
    assert d.needs_manual_review() is True
    assert len(d.candidates) == 2


def test_nothing_recognised() -> None:
    d = detect_nvt_number(filename="foto.jpg", ocr_text="Nur Text")
    assert d.nvt_number is None
    assert d.needs_manual_review() is True
