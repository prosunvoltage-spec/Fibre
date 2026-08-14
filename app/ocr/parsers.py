"""Regex- und Heuristik-basierte Extraktion strukturierter Felder aus OCR-Text.

Extrahiert aus dem Rohtext eines ``OcrResult``:

* NVT-Nummer (aus Typenschild oder Kamera-App-Overlay)
* Deutsche Adresse (Straße, Hausnummer, PLZ, Ort)
* GPS-Koordinaten (Dezimalgrad, auch mit deutschem Komma)
* Aufnahmedatum/-uhrzeit (deutsches Format)

Grundregel: Wir raten nichts. Wenn eine Zahl mehrdeutig ist (z.B. 5-stellig
und in Adress-Nähe → eher PLZ als NVT-Nummer), gibt der Parser lieber
``None`` zurück. Widersprüche (mehrere Kandidaten für dasselbe Feld)
landen in ``warnings``. Der Aufrufer entscheidet, ob das ausreicht oder
zu ``MANUELLE_PRUEFUNG_ERFORDERLICH`` führt.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field

from app.ocr.base import OcrResult

# ---------------------------------------------------------------------------
# Ergebnis-Typ
# ---------------------------------------------------------------------------


class ParsedOverlay(BaseModel):
    """Strukturierte Felder, die aus dem Foto-Text extrahiert wurden."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nvt_number: str | None = None
    nvt_number_candidates: list[str] = Field(default_factory=list)

    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    city: str | None = None

    gps_lat: Decimal | None = None
    gps_lon: Decimal | None = None

    captured_at: datetime | None = None

    warnings: list[str] = Field(default_factory=list)

    @property
    def has_address(self) -> bool:
        return bool(self.postal_code or self.city or self.street)

    @property
    def has_gps(self) -> bool:
        return self.gps_lat is not None and self.gps_lon is not None


# ---------------------------------------------------------------------------
# Einzel-Parser
# ---------------------------------------------------------------------------

# NVT-Nummer: erlaubt "NVT 7101", "NVT-7101", "NVT_7101", "NVT7101" (case-insensitive).
# Auch "Netzverteiler 7101" — aber immer mit Prefix, damit wir nicht mit PLZ verwechseln.
_NVT_RE = re.compile(
    r"\b(?:NVT|N\.?V\.?T\.?|Netzverteiler)[\s._\-#:]*([0-9O]{3,5}[A-Za-z]?)\b",
    re.IGNORECASE,
)

# GPS Dezimalgrad. Deutsches Komma zulässig ("51,96 N 7,51 E"), auch simples "51.96, 7.51".
_GPS_LABELED_RE = re.compile(
    r"([NS])\s*([0-9]{1,2}[.,][0-9]{1,7})[°\s]*[,;]?\s*"
    r"([EWO])\s*([0-9]{1,3}[.,][0-9]{1,7})",
    re.IGNORECASE,
)
_GPS_PLAIN_RE = re.compile(
    r"(?<![0-9.])([+-]?[0-9]{1,2}[.,][0-9]{1,7})\s*[,;/]\s*"
    r"([+-]?[0-9]{1,3}[.,][0-9]{1,7})(?![0-9.])"
)

# PLZ + Ort. PLZ = 5 Ziffern, Ort mind. 2 Buchstaben, darf Umlaute/Bindestrich/Leerzeichen enthalten.
_PLZ_CITY_RE = re.compile(
    r"\b([0-9]{5})\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-\.\s]{1,60}?)"
    r"(?=$|[,;\n]|\s{2,}|\s+[0-9]|\s+GPS|\s+Foto|\s+Bild)"
)

# Straße + Hausnummer. Erkennt gängige Endungen; Hausnummer 1-4 Ziffern + optional Buchstabe/Bindestrich.
# case-insensitive, damit "Straße"/"straße"/"STRASSE" gleichermaßen matched.
_STREET_HOUSE_RE = re.compile(
    r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-\.\s]{2,60}?"
    r"(?:stra(?:ß|ss)e|str\.?|weg|platz|allee|ring|gasse|damm|ufer|hof|"
    r"pfad|steig|chaussee|promenade))"
    r"\s+([0-9]{1,4}(?:\s*[a-hA-H])?(?:\s*[\-–]\s*[0-9]{1,4}[a-hA-H]?)?)\b",
    re.IGNORECASE,
)

# Datum + optional Uhrzeit. Deutsches Format: "13.08.2026", "13.08.2026 14:32[:15]".
_DATE_RE = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])\.(0?[1-9]|1[0-2])\.(20[2-9][0-9])"
    r"(?:[\s,;/T]+([01]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?)?\b"
)

_ISO_DATE_RE = re.compile(
    r"\b(20[2-9][0-9])-(0?[1-9]|1[0-2])-(0?[1-9]|[12][0-9]|3[01])"
    r"(?:[\sT]+([01]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?)?\b"
)


def _clean_ocr_digits(raw: str) -> str:
    """Behandelt typische OCR-Verwechsler in *rein numerischem* Kontext."""
    return raw.replace("O", "0").replace("o", "0")


def parse_nvt_numbers(text: str) -> list[str]:
    """Alle NVT-Nummer-Kandidaten (dedupliziert, Reihenfolge stabil)."""
    seen: dict[str, None] = {}
    for match in _NVT_RE.finditer(text):
        raw = match.group(1)
        cleaned = _clean_ocr_digits(raw)
        if cleaned.isdigit() or (cleaned[:-1].isdigit() and cleaned[-1].isalpha()):
            seen.setdefault(cleaned, None)
    return list(seen.keys())


def _decimal_from_str(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def parse_gps(text: str) -> tuple[Decimal, Decimal] | None:
    """Liefert (lat, lon) als Dezimalgrad oder ``None``."""
    m = _GPS_LABELED_RE.search(text)
    if m:
        lat_hem, lat_str, lon_hem, lon_str = m.groups()
        lat = _decimal_from_str(lat_str)
        lon = _decimal_from_str(lon_str)
        if lat is None or lon is None:
            return None
        if lat_hem.upper() == "S":
            lat = -lat
        if lon_hem.upper() in ("W",):
            lon = -lon
        if _valid_wgs84(lat, lon):
            return lat, lon
    m = _GPS_PLAIN_RE.search(text)
    if m:
        lat = _decimal_from_str(m.group(1))
        lon = _decimal_from_str(m.group(2))
        if lat is None or lon is None:
            return None
        if _valid_wgs84(lat, lon):
            return lat, lon
    return None


def _valid_wgs84(lat: Decimal, lon: Decimal) -> bool:
    return Decimal("-90") <= lat <= Decimal("90") and Decimal("-180") <= lon <= Decimal("180")


def parse_address(text: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Extrahiert (street, house_number, postal_code, city)."""
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    city: str | None = None

    m = _STREET_HOUSE_RE.search(text)
    if m:
        street = _normalize_whitespace(m.group(1))
        house_number = _normalize_whitespace(m.group(2))

    m = _PLZ_CITY_RE.search(text)
    if m:
        postal_code = m.group(1)
        city = _normalize_whitespace(m.group(2))
        # City auf ein/zwei Wörter kappen, wenn nach dem 2. Wort typischer Overlay-Kram folgt.
        city = _trim_city(city)

    return street, house_number, postal_code, city


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" ,.-;")


def _trim_city(city: str) -> str:
    parts = city.split()
    # gängige deutsche Ortsnamen bis 4 Wörter (z.B. "Frankfurt am Main")
    return " ".join(parts[:4])


def parse_datetime(text: str) -> datetime | None:
    """Erstes plausibles Datum aus dem Text."""
    m = _DATE_RE.search(text)
    if m:
        day, month, year, hh, mm, ss = m.groups()
        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hh) if hh else 0,
                int(mm) if mm else 0,
                int(ss) if ss else 0,
            )
        except ValueError:
            pass
    m = _ISO_DATE_RE.search(text)
    if m:
        year, month, day, hh, mm, ss = m.groups()
        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hh) if hh else 0,
                int(mm) if mm else 0,
                int(ss) if ss else 0,
            )
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# High-Level
# ---------------------------------------------------------------------------


def parse_overlay(ocr: OcrResult | str) -> ParsedOverlay:
    """Ein Aufruf → alle Felder. Widersprüche → ``warnings``."""
    text = ocr.text if isinstance(ocr, OcrResult) else ocr

    nvt_candidates = parse_nvt_numbers(text)
    warnings: list[str] = []
    nvt_number = None
    if nvt_candidates:
        nvt_number = nvt_candidates[0]
        if len(nvt_candidates) > 1:
            warnings.append(
                f"Mehrere NVT-Nummern im OCR erkannt: {', '.join(nvt_candidates)}"
            )

    street, house_number, postal_code, city = parse_address(text)
    gps = parse_gps(text)
    captured_at = parse_datetime(text)

    return ParsedOverlay(
        nvt_number=nvt_number,
        nvt_number_candidates=nvt_candidates,
        street=street,
        house_number=house_number,
        postal_code=postal_code,
        city=city,
        gps_lat=gps[0] if gps else None,
        gps_lon=gps[1] if gps else None,
        captured_at=captured_at,
        warnings=warnings,
    )
