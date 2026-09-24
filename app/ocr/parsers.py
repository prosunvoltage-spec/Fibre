"""Regex-Extraktion strukturierter Felder aus OCR-Rohtext.

Extrahiert werden möglichst konservativ: bei Unsicherheit lieber ``None``
zurückgeben und den Rohtext an anderer Stelle weiterreichen. Erfindet keine
Werte.

Erkannte Felder:
- NVT-Nummer (4-stellig, häufigstes Muster: ``NVT 7107``, ``NVT-7107`` …)
- Straße + Hausnummer (aus Kamera-Overlay-Zeilen)
- PLZ + Ort (5 Ziffern gefolgt von Ort)
- GPS-Koordinaten (Dezimalgrad, z.B. ``51.9488, 7.53963``)
- Datum + Uhrzeit
- Regelplan-Label (falls es im Foto steht: ``B2/2``, ``VZP1``, …)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractedText:
    """Strukturierte Extraktion aus OCR-Rohtext."""

    nvt_numbers: list[str] = field(default_factory=list)
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    captured_at: datetime | None = None
    ruleplan_label: str | None = None
    raw: str = ""

    def has_single_nvt(self) -> bool:
        return len(self.nvt_numbers) == 1

    def to_dict(self) -> dict:
        return {
            "nvt_numbers": self.nvt_numbers,
            "street": self.street,
            "house_number": self.house_number,
            "postal_code": self.postal_code,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "ruleplan_label": self.ruleplan_label,
        }


# ---------------------------------------------------------------------------
# Regex-Katalog
# ---------------------------------------------------------------------------

# NVT-Nummer: 4-stellige Zahl mit vorangestelltem NVT-Marker
_NVT_PATTERN = re.compile(
    r"""
    (?<![A-Z0-9])              # Kein Wortzeichen davor
    (?:NVT|N\.V\.T\.?|NvT)     # Marker
    [\s\-.:_/]{0,3}            # Trennzeichen
    (\d{4})                    # 4-stellige Nummer
    (?![0-9])
    """,
    re.IGNORECASE | re.VERBOSE,
)

# 5-stellige PLZ gefolgt von Ort (bis Zeilenende, max. 40 Zeichen)
_PLZ_ORT_PATTERN = re.compile(
    r"\b(?P<plz>\d{5})\s+(?P<ort>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-.\s]{1,39})",
)

# Straße Hausnummer: „Roxeler Straße 579", „Am Rohrbusch 22", „Buchenweg 22a"
_STREET_PATTERN = re.compile(
    r"""
    (?P<street>
        (?:[A-ZÄÖÜ][a-zäöüß\-\.]+\s?){1,4}
        (?:straße|strasse|str\.?|weg|allee|platz|damm|kamp|stiege|stieg|
           gasse|ring|hof|dorn|garten|feld|park|ufer|berg|höhe|hoehe|
           siedlung|steig|breite|graben|winkel|kämpken|kampken)
    )
    \s+
    (?P<nr>\d+[A-Za-z]?(?:\s?[-–]\s?\d+[A-Za-z]?)?)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# GPS in Dezimalgrad: „51.9488, 7.53963" oder „51,9488  7,53963"
_GPS_PATTERN = re.compile(
    r"""
    (?<![\d\.])
    (?P<lat>-?\d{1,2}[.,]\d{3,7})
    \s*[,;\s]\s*
    (?P<lon>-?\d{1,3}[.,]\d{3,7})
    (?![\d\.])
    """,
    re.VERBOSE,
)

# Datum + Uhrzeit: „19.02.2026, 15:01:25" oder „19.02.2026 15:01"
_DATE_TIME_PATTERN = re.compile(
    r"(?P<d>\d{1,2})\.(?P<m>\d{1,2})\.(?P<y>\d{4}),?\s+"
    r"(?P<H>\d{1,2}):(?P<M>\d{2})(?::(?P<S>\d{2}))?"
)

# Regelplan-Label wie im Foto beschriftet: „Regelplan B2/2", „Regelplan: VZP1"
_RULEPLAN_PATTERN = re.compile(
    r"""
    Regelplan[:\s]*
    (?P<label>
        B\s?[IVX12]{1,3}\s?/\s?\d{1,3}    # z.B. B2/2, B I/15
        | VZP\s?\d+                       # VZP1, VZP 2
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Extraktion
# ---------------------------------------------------------------------------


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            result.append(it)
    return result


def extract_nvt_numbers(text: str) -> list[str]:
    """Alle 4-stelligen NVT-Nummern (dedupliziert, in Erscheinungsreihenfolge)."""
    return _dedup_preserve_order(_NVT_PATTERN.findall(text))


def extract_nvt_from_filename(filename: str) -> str | None:
    """Erkennt NVT-Nummer aus Dateinamen wie ``NVT_7107.jpg`` oder ``nvt-7107_01.jpg``."""
    stem = filename.rsplit("/", 1)[-1]
    stem = stem.rsplit("\\", 1)[-1]
    match = _NVT_PATTERN.search(stem)
    if match:
        return match.group(1)
    # Reine 4-stellige Zahl als eigenes Segment, z.B. "7107_01.jpg"
    m2 = re.match(r"^(\d{4})[\s._\-]", stem)
    if m2:
        return m2.group(1)
    return None


def extract_structured(text: str) -> ExtractedText:
    """Führt alle Regex-Extraktionen auf einem Rohtext durch."""
    result = ExtractedText(raw=text)

    result.nvt_numbers = extract_nvt_numbers(text)

    # PLZ + Ort
    for m in _PLZ_ORT_PATTERN.finditer(text):
        plz = m.group("plz")
        ort = m.group("ort").strip().rstrip(",;")
        # Kein „Deutschland" oder ähnlich generisch
        if ort.lower() not in {"deutschland", "germany", "de"}:
            result.postal_code = plz
            result.city = ort.split("\n", 1)[0].strip()
            break

    # Straße + Hausnummer
    m = _STREET_PATTERN.search(text)
    if m:
        result.street = re.sub(r"\s+", " ", m.group("street")).strip()
        result.house_number = m.group("nr").strip()

    # GPS
    m = _GPS_PATTERN.search(text)
    if m:
        try:
            lat = float(m.group("lat").replace(",", "."))
            lon = float(m.group("lon").replace(",", "."))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                result.latitude = lat
                result.longitude = lon
        except ValueError:
            pass

    # Datum + Uhrzeit
    m = _DATE_TIME_PATTERN.search(text)
    if m:
        try:
            result.captured_at = datetime(
                year=int(m.group("y")),
                month=int(m.group("m")),
                day=int(m.group("d")),
                hour=int(m.group("H")),
                minute=int(m.group("M")),
                second=int(m.group("S") or 0),
            )
        except ValueError:
            pass

    # Regelplan-Label (optional; nie als Entscheidung verwenden)
    m = _RULEPLAN_PATTERN.search(text)
    if m:
        # Whitespace innerhalb normalisieren: „B I/ 2" → „B I/2"
        result.ruleplan_label = re.sub(r"\s+", "", m.group("label")).upper()

    return result
