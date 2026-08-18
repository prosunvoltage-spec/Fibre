"""Foto-Verarbeitung: EXIF, GPS, SHA-256, Kopie nach Ablageordner."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError


class PhotoProcessingError(Exception):
    pass


@dataclass
class PhotoInfo:
    """Ergebnis der Basis-Verarbeitung eines Fotos."""

    original_filename: str
    stored_path: Path
    mime_type: str
    width: int
    height: int
    sha256: str
    exif: dict[str, Any] = field(default_factory=dict)
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    captured_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)


_MIME_BY_EXT: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}


def _sha256(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _rational_to_float(value: Any) -> float | None:
    try:
        if isinstance(value, tuple) and len(value) == 2:
            num, denom = value
            return float(num) / float(denom) if denom else None
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _dms_to_decimal(dms: Any, ref: str | None) -> float | None:
    try:
        deg = _rational_to_float(dms[0])
        minute = _rational_to_float(dms[1])
        sec = _rational_to_float(dms[2])
        if deg is None or minute is None or sec is None:
            return None
        decimal = deg + minute / 60.0 + sec / 3600.0
        if ref and ref.upper() in ("S", "W"):
            decimal = -decimal
        return decimal
    except (TypeError, IndexError):
        return None


def _extract_gps(exif: dict[str, Any]) -> tuple[float | None, float | None]:
    gps_info = exif.get("GPSInfo")
    if not isinstance(gps_info, dict):
        return None, None
    # GPS-Tags in lesbare Namen umbenennen
    gps: dict[str, Any] = {}
    for tag_id, value in gps_info.items():
        name = ExifTags.GPSTAGS.get(tag_id, tag_id)
        gps[name] = value

    lat = _dms_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
    lon = _dms_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
    if lat is None or not (-90 <= lat <= 90):
        lat = None
    if lon is None or not (-180 <= lon <= 180):
        lon = None
    return lat, lon


def _extract_captured_at(exif: dict[str, Any]) -> datetime | None:
    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        raw = exif.get(key)
        if not raw:
            continue
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(raw), fmt)
            except ValueError:
                continue
    return None


def _read_exif(image: Image.Image) -> dict[str, Any]:
    try:
        raw_exif = image._getexif()
    except AttributeError:
        return {}
    if not raw_exif:
        return {}
    named: dict[str, Any] = {}
    for tag_id, value in raw_exif.items():
        name = ExifTags.TAGS.get(tag_id, str(tag_id))
        # GPS bleibt als dict — Byte-Werte werden zu str
        if name == "GPSInfo":
            named[name] = dict(value)
        else:
            named[name] = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    return named


def _sanitize_for_json(exif: dict[str, Any]) -> dict[str, Any]:
    """Wandelt Exif-Werte in JSON-freundliche Typen."""
    out: dict[str, Any] = {}
    for key, value in exif.items():
        try:
            if isinstance(value, bytes):
                out[str(key)] = value.decode("utf-8", errors="replace")
            elif isinstance(value, tuple):
                out[str(key)] = [
                    _rational_to_float(v) if isinstance(v, tuple) else str(v) for v in value
                ]
            elif isinstance(value, dict):
                out[str(key)] = _sanitize_for_json(value)
            elif isinstance(value, (int, float, str, bool)) or value is None:
                out[str(key)] = value
            else:
                out[str(key)] = str(value)
        except Exception:  # pragma: no cover — Exif hat Randfälle
            out[str(key)] = str(value)
    return out


def process_photo(
    source: Path,
    project_input_dir: Path,
    relative_group: str | None = None,
) -> PhotoInfo:
    """Kopiert Foto nach ``project_input_dir[/group]``, liest EXIF und Meta.

    - ``source`` bleibt unverändert (Master-Prompt §14, Build-Prompt §78).
    - Zielpfad ergibt sich aus dem ursprünglichen Dateinamen; bei
      Namenskollision wird ein Suffix angehängt.
    - Gibt :class:`PhotoInfo` zurück, ohne DB-Kontakt.
    """
    if not source.is_file():
        raise PhotoProcessingError(f"Datei fehlt: {source}")

    suffix = source.suffix.lower()
    mime_type = _MIME_BY_EXT.get(suffix)
    if mime_type is None:
        raise PhotoProcessingError(f"MIME-Typ nicht unterstützt: {suffix}")

    warnings: list[str] = []

    try:
        with Image.open(source) as img:
            img.load()
            width, height = img.size
            exif = _read_exif(img)
    except UnidentifiedImageError as exc:
        raise PhotoProcessingError(f"Kein gültiges Bild: {source}") from exc

    sha = _sha256(source)

    target_dir = project_input_dir
    if relative_group:
        target_dir = project_input_dir / relative_group
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / source.name
    if target.exists() and _sha256(target) != sha:
        # Namenskollision, aber anderer Inhalt: eindeutig machen
        stem = target.stem
        i = 1
        while (candidate := target_dir / f"{stem}__{i}{suffix}").exists():
            i += 1
        target = candidate
    if not target.exists():
        shutil.copyfile(source, target)

    lat, lon = _extract_gps(exif)
    captured_at = _extract_captured_at(exif)

    return PhotoInfo(
        original_filename=source.name,
        stored_path=target,
        mime_type=mime_type,
        width=width,
        height=height,
        sha256=sha,
        exif=_sanitize_for_json(exif),
        gps_latitude=lat,
        gps_longitude=lon,
        captured_at=captured_at,
        warnings=warnings,
    )
