"""Zuordnung Foto → NVT-Nummer mit Prioritätskette.

Reihenfolge (nach ``docs/PROJECT_PLAN.md`` Phase 4):

1. **User-Override**  — explizit vom Bediener beim Upload gesetzt
2. **Ordnername**     — Layout ``NVT_7101/01.jpg`` (aus Ingest-Hint)
3. **Dateiname**      — Layout ``NVT_7101.jpg``
4. **OCR-Text**       — nur wenn genau *eine* NVT-Nummer sicher lesbar ist

Vision (Phase 5) ist explizit nicht Teil dieser Kette — dieses Modul
läuft ohne Netz und ohne LLM.

Widerspruch zwischen zwei Ebenen: die höhere gewinnt, aber es entsteht
eine ``warning``. Mehrere unterschiedliche NVT-Nummern im OCR-Text ohne
höherwertige Quelle → keine Zuweisung, Warnung
``MANUELLE_PRUEFUNG_ERFORDERLICH``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.ocr.base import OcrResult
from app.ocr.parsers import ParsedOverlay, parse_overlay
from app.uploads.ingest import IngestedPhoto


class NvtIdSource(str, Enum):
    """Woher die zugeordnete NVT-Nummer stammt."""

    USER = "user"
    FOLDER = "folder"
    FILENAME = "filename"
    OCR = "ocr"
    NONE = "none"


@dataclass(slots=True)
class NvtAssignment:
    """Ergebnis der Zuordnung eines einzelnen Fotos."""

    photo: IngestedPhoto
    nvt_number: str | None
    source: NvtIdSource
    warnings: list[str] = field(default_factory=list)
    parsed_overlay: ParsedOverlay | None = None
    manual_review_required: bool = False


def detect_nvt(
    photo: IngestedPhoto,
    ocr: OcrResult | None,
    *,
    user_override: str | None = None,
) -> NvtAssignment:
    """Führt die Prioritätskette für ein Foto aus."""

    warnings: list[str] = []
    parsed = parse_overlay(ocr) if ocr is not None else None

    ocr_number = parsed.nvt_number if parsed else None
    ocr_candidates = parsed.nvt_number_candidates if parsed else []

    def _diff(name: str, higher: str, lower: str | None) -> None:
        if lower and _normalize(lower) != _normalize(higher):
            warnings.append(
                f"NVT-Widerspruch: {name}={lower} ignoriert (User/Ordner/Datei sagt {higher})"
            )

    # 1. User-Override
    if user_override:
        chosen = _normalize(user_override)
        _diff("Ordner", chosen, photo.folder_nvt_hint)
        _diff("Datei", chosen, photo.filename_nvt_hint)
        _diff("OCR", chosen, ocr_number)
        return NvtAssignment(
            photo=photo,
            nvt_number=chosen,
            source=NvtIdSource.USER,
            warnings=warnings,
            parsed_overlay=parsed,
        )

    # 2. Ordnername
    if photo.folder_nvt_hint:
        chosen = _normalize(photo.folder_nvt_hint)
        _diff("Datei", chosen, photo.filename_nvt_hint)
        _diff("OCR", chosen, ocr_number)
        return NvtAssignment(
            photo=photo,
            nvt_number=chosen,
            source=NvtIdSource.FOLDER,
            warnings=warnings,
            parsed_overlay=parsed,
        )

    # 3. Dateiname
    if photo.filename_nvt_hint:
        chosen = _normalize(photo.filename_nvt_hint)
        _diff("OCR", chosen, ocr_number)
        return NvtAssignment(
            photo=photo,
            nvt_number=chosen,
            source=NvtIdSource.FILENAME,
            warnings=warnings,
            parsed_overlay=parsed,
        )

    # 4. OCR — nur wenn genau EINE Nummer eindeutig ist
    if len(ocr_candidates) == 1:
        return NvtAssignment(
            photo=photo,
            nvt_number=_normalize(ocr_candidates[0]),
            source=NvtIdSource.OCR,
            warnings=warnings,
            parsed_overlay=parsed,
        )
    if len(ocr_candidates) > 1:
        warnings.append(
            "MANUELLE_PRUEFUNG_ERFORDERLICH: mehrere NVT-Nummern im Foto und keine "
            "höherwertige Quelle (User/Ordner/Dateiname) verfügbar: "
            + ", ".join(ocr_candidates)
        )
        return NvtAssignment(
            photo=photo,
            nvt_number=None,
            source=NvtIdSource.NONE,
            warnings=warnings,
            parsed_overlay=parsed,
            manual_review_required=True,
        )

    # Nichts gefunden
    warnings.append(
        "Kein NVT-Hinweis: weder Ordner-, Datei- noch OCR-Erkennung liefert eine Nummer. "
        "Manuelle Zuordnung erforderlich."
    )
    return NvtAssignment(
        photo=photo,
        nvt_number=None,
        source=NvtIdSource.NONE,
        warnings=warnings,
        parsed_overlay=parsed,
        manual_review_required=True,
    )


def _normalize(nvt: str) -> str:
    """Vereinheitlicht die NVT-Nummer (uppercase, keine Trennzeichen)."""
    return nvt.strip().upper()
