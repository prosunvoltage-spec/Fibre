"""OCR-Provider-Interface. Konkrete Provider (Tesseract, Cloud) implementieren es."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class OCRResult:
    """Rohes OCR-Ergebnis eines einzelnen Fotos."""

    text: str
    confidence: float = 0.0  # 0..1, sofern der Provider das liefert
    language: str = ""
    provider: str = ""
    words: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.text.strip()


class OCRProvider(Protocol):
    """Vertrag für alle OCR-Adapter."""

    id: str

    def ocr_photo(self, photo_path: Path) -> OCRResult: ...
