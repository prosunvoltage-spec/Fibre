"""Test-Provider mit vordefinierten OCR-Antworten.

Nützt Contract-Tests und Fixtures: statt echtem Tesseract-Aufruf wird das
Ergebnis anhand des SHA-256 des Foto-Bytes nachgeschlagen.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from app.ocr.base import OcrResult


class MockOCRProvider:
    """Liefert vordefinierte ``OcrResult`` je nach SHA-256 des Inputs."""

    id = "mock"
    version = "1"

    def __init__(self, responses: Mapping[str, OcrResult]) -> None:
        self._responses = dict(responses)

    def ocr_photo(self, image_bytes: bytes, *, language: str = "deu+eng") -> OcrResult:
        digest = hashlib.sha256(image_bytes).hexdigest()
        if digest not in self._responses:
            raise KeyError(
                f"Kein Mock-OCR-Ergebnis fuer sha256={digest} hinterlegt "
                f"(hast du das Fixture registriert?)"
            )
        base = self._responses[digest]
        return base.model_copy(update={"language": language})
