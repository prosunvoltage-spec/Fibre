"""OCR-Adapter für den Text-in-Bild-Kanal.

Die Provider hinter ``OCRProvider`` sind austauschbar; ``TesseractProvider``
ist der Default (offline). Ergebnisse werden ausschließlich in Feldern nach
``docs/DATA_MODEL.md §2.5`` (``Photo.ocr_json``) persistiert.
"""

from app.ocr.base import (
    OCRProvider,
    OcrResult,
    TextBlock,
)


def build_default_ocr_provider() -> OCRProvider:
    """Fabrik für den in ``Settings.ocr_provider`` konfigurierten Provider."""
    from app.config import get_settings

    name = get_settings().ocr_provider.lower()
    if name == "tesseract":
        from app.ocr.tesseract_provider import TesseractOCRProvider

        return TesseractOCRProvider()
    raise ValueError(f"Unbekannter OCR-Provider: {name}")


__all__ = [
    "OCRProvider",
    "OcrResult",
    "TextBlock",
    "build_default_ocr_provider",
]
