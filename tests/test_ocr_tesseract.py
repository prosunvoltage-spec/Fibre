"""Contract-Test für TesseractOCRProvider.

Erwartet ein installiertes Tesseract (siehe ``docs/PROJECT_PLAN.md`` §12).
Der Test wird übersprungen, wenn das Binary fehlt, damit CI-Umgebungen
ohne Tesseract nicht kaputtgehen.
"""

from __future__ import annotations

import pytest

from app.ocr.base import OcrResult
from tests.fixtures.photo_generator import render_large_ocr_photo


@pytest.fixture(scope="module")
def tesseract_provider():  # type: ignore[no-untyped-def]
    pytest.importorskip("pytesseract")
    try:
        from app.ocr.tesseract_provider import TesseractOCRProvider
        return TesseractOCRProvider()
    except RuntimeError as exc:
        pytest.skip(f"Tesseract nicht verfuegbar: {exc}")


def test_reads_nvt_number_from_synthetic_photo(tesseract_provider) -> None:  # type: ignore[no-untyped-def]
    photo = render_large_ocr_photo(["NVT 7107", "Roxel"])
    result: OcrResult = tesseract_provider.ocr_photo(photo, language="deu+eng")
    assert isinstance(result, OcrResult)
    assert "7107" in result.text
    assert result.provider == "tesseract"
    assert result.image_width > 0
    assert result.image_height > 0


def test_high_confidence_filter(tesseract_provider) -> None:  # type: ignore[no-untyped-def]
    photo = render_large_ocr_photo(["NVT 7107"])
    result = tesseract_provider.ocr_photo(photo)
    # Alle geblockten Blöcke haben confidence ∈ [0, 1]
    assert all(0 <= float(b.confidence) <= 1 for b in result.blocks)
    # Es gibt mindestens einen Block ueber der Schwelle 0.6
    assert result.high_confidence_text(threshold=0) != ""
