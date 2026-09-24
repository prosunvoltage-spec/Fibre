"""NVT-Erkennung mit Prioritätskette.

Prioritätsreihenfolge (Build-Prompt §12):
   User > Dateiname > Ordnername > OCR > (Vision — Phase 5)

Bei Konflikten (mehrere NVT-Nummern in einer Quelle) wird eine
Warnung erzeugt; Aufrufer muss den Fall auf ``MANUELLE_PRÜFUNG`` heben.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from app.ocr.parsers import extract_nvt_from_filename, extract_nvt_numbers


class NvtDetectionSource(str, Enum):
    USER = "user"
    FILENAME = "filename"
    FOLDER = "folder"
    OCR = "ocr"
    VISION = "vision"


@dataclass(frozen=True)
class NvtDetection:
    """Ergebnis der NVT-Erkennung für ein einzelnes Foto."""

    nvt_number: str | None
    source: NvtDetectionSource | None
    candidates: list[str] = field(default_factory=list)  # alle beobachteten NVT-Nummern
    warnings: list[str] = field(default_factory=list)

    def needs_manual_review(self) -> bool:
        return self.nvt_number is None or len(self.candidates) > 1


_FOLDER_NVT_PATTERN = re.compile(r"NVT[\s_\-]?(\d{4})", re.IGNORECASE)


def _extract_from_folder(rel_dir: str) -> str | None:
    if not rel_dir:
        return None
    for part in Path(rel_dir).parts:
        m = _FOLDER_NVT_PATTERN.search(part)
        if m:
            return m.group(1)
    return None


def detect_nvt_number(
    *,
    filename: str,
    relative_dir: str = "",
    ocr_text: str = "",
    user_override: str | None = None,
) -> NvtDetection:
    """Ermittelt die NVT-Nummer für ein einzelnes Foto.

    - ``user_override`` gewinnt immer, bekommt aber trotzdem alle Kandidaten
      zur Kenntnis.
    - Bei mehreren NVT-Nummern im OCR-Text: keine automatische Auswahl,
      stattdessen ``needs_manual_review = True``.
    """
    warnings: list[str] = []

    ocr_candidates = extract_nvt_numbers(ocr_text) if ocr_text else []
    filename_candidate = extract_nvt_from_filename(filename)
    folder_candidate = _extract_from_folder(relative_dir)

    # Alle Kandidaten sammeln (in Prioritätsreihenfolge)
    all_candidates: list[str] = []
    if user_override:
        all_candidates.append(user_override)
    if filename_candidate:
        all_candidates.append(filename_candidate)
    if folder_candidate and folder_candidate not in all_candidates:
        all_candidates.append(folder_candidate)
    for c in ocr_candidates:
        if c not in all_candidates:
            all_candidates.append(c)

    # Konfliktprüfung: unterschiedliche NVT-Nummern erkannt?
    unique = set(all_candidates)
    if len(unique) > 1:
        warnings.append(
            f"Mehrere NVT-Nummern erkannt: {', '.join(sorted(unique))} — "
            "manuelle Prüfung erforderlich"
        )

    # Prioritätskette
    if user_override:
        return NvtDetection(
            nvt_number=user_override,
            source=NvtDetectionSource.USER,
            candidates=all_candidates,
            warnings=warnings,
        )
    if filename_candidate:
        return NvtDetection(
            nvt_number=filename_candidate,
            source=NvtDetectionSource.FILENAME,
            candidates=all_candidates,
            warnings=warnings,
        )
    if folder_candidate:
        return NvtDetection(
            nvt_number=folder_candidate,
            source=NvtDetectionSource.FOLDER,
            candidates=all_candidates,
            warnings=warnings,
        )
    if len(ocr_candidates) == 1:
        return NvtDetection(
            nvt_number=ocr_candidates[0],
            source=NvtDetectionSource.OCR,
            candidates=all_candidates,
            warnings=warnings,
        )
    if len(ocr_candidates) > 1:
        warnings.append(
            "OCR fand mehrere NVT-Nummern; keine automatische Auswahl"
        )
        return NvtDetection(
            nvt_number=None,
            source=None,
            candidates=all_candidates,
            warnings=warnings,
        )

    warnings.append("Keine NVT-Nummer erkennbar (Dateiname/Ordner/OCR)")
    return NvtDetection(
        nvt_number=None,
        source=None,
        candidates=all_candidates,
        warnings=warnings,
    )


@dataclass
class PhotoAssignment:
    """Zuordnung eines Fotos zu einem NVT (oder ``None`` bei unklarem Fall)."""

    photo_path: Path
    relative_dir: str
    detection: NvtDetection


def group_photos_by_nvt(
    assignments: Sequence[PhotoAssignment],
) -> dict[str | None, list[PhotoAssignment]]:
    """Gruppiert erkannte Fotos nach NVT-Nummer. ``None`` sammelt Zweifelsfälle."""
    grouped: dict[str | None, list[PhotoAssignment]] = defaultdict(list)
    for a in assignments:
        grouped[a.detection.nvt_number].append(a)
    return dict(grouped)


def iter_detections(
    photos: Iterable[tuple[str, str, str]],
) -> list[PhotoAssignment]:  # pragma: no cover — Convenience-Wrapper
    """Für Tests: kompakte Erzeugung von PhotoAssignments aus (filename, rel_dir, ocr).

    Nicht in Produktivpfaden verwenden — dort läuft der Detector über echte
    Foto-Objekte im UploadService.
    """
    result: list[PhotoAssignment] = []
    for filename, rel_dir, ocr in photos:
        detection = detect_nvt_number(filename=filename, relative_dir=rel_dir, ocr_text=ocr)
        result.append(PhotoAssignment(Path(filename), rel_dir, detection))
    return result
