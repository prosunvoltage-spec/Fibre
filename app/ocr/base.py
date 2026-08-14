"""OCR-Provider-Interface und Ergebnis-Datentypen.

Reines Interface — kein I/O, keine Netzwerk-Aufrufe. Konkrete Adapter
liegen in ``app/ocr/tesseract_provider.py`` (Default) bzw.
``app/ocr/mock_provider.py`` (für Tests).

Alle Ergebnisse sind vollständig serialisierbar (Pydantic) und landen
1:1 als ``Photo.ocr_json`` in der DB (siehe ``docs/DATA_MODEL.md §2.5``).
Der Rohausgabe-Kanal ``raw`` steht Provider-frei zur Verfügung, wird aber
nur im internen Prüfbericht ausgewertet, nie im finalen Word-Dokument.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Strict(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=False,
    )


class TextBlock(_Strict):
    """Ein erkanntes Textstück mit Position und Konfidenz.

    ``bbox`` ist auf ``[0, 1]`` normalisiert (relativ zu Bildbreite/-höhe),
    damit das Ergebnis auflösungsunabhängig ist. ``confidence`` ist auf
    ``[0, 1]`` skaliert (Tesseract liefert 0-100, wird geteilt durch 100).
    """

    text: str
    bbox_x: Decimal
    bbox_y: Decimal
    bbox_w: Decimal
    bbox_h: Decimal
    confidence: Decimal
    line: int = 0

    @field_validator("bbox_x", "bbox_y", "bbox_w", "bbox_h", "confidence")
    @classmethod
    def _unit_interval(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("Wert muss in [0, 1] liegen")
        return v


class OcrResult(_Strict):
    """Aggregiertes OCR-Ergebnis für ein Foto."""

    text: str
    blocks: list[TextBlock] = Field(default_factory=list)
    language: str = "deu"
    provider: str
    provider_version: str
    image_width: int = Field(ge=1)
    image_height: int = Field(ge=1)
    raw: dict[str, Any] = Field(default_factory=dict)

    def high_confidence_text(self, threshold: Decimal = Decimal("0.6")) -> str:
        """Text nur aus Blöcken mit Konfidenz >= ``threshold``."""
        return " ".join(b.text for b in self.blocks if b.confidence >= threshold)


@runtime_checkable
class OCRProvider(Protocol):
    """Vertrag für alle OCR-Adapter.

    ``id`` und ``version`` fließen in Audit- und Reproduzierbarkeits-Logs
    (siehe ``docs/ARCHITECTURE.md §5.3``).
    """

    id: str
    version: str

    def ocr_photo(self, image_bytes: bytes, *, language: str = "deu+eng") -> OcrResult:
        """Erkennt Text in einem einzelnen Foto.

        ``language`` folgt der Tesseract-Notation (`deu`, `eng`, `deu+eng`).
        Andere Provider dürfen den Wert ignorieren, müssen aber den
        angeforderten Wert im Ergebnis (``OcrResult.language``) spiegeln.
        """
        ...
