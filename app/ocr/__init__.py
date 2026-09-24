"""OCR-Adapter (austauschbar). Default: Tesseract."""

from app.ocr.base import OCRProvider, OCRResult
from app.ocr.parsers import ExtractedText, extract_structured
from app.ocr.tesseract_provider import TesseractOCRProvider

__all__ = [
    "ExtractedText",
    "OCRProvider",
    "OCRResult",
    "TesseractOCRProvider",
    "extract_structured",
]
