"""Upload-Ingest: ZIP oder Ordner-Tree → normalisierte ``IngestedPhoto``-Liste.

Verantwortlichkeiten:

* ZIP entpacken (mit Zip-Slip-Schutz)
* Ordner-Tree rekursiv scannen
* Beide Layouts nach Build-Prompt §11 erkennen:
  - **Flach:**       ``NVT_7101.jpg``
  - **Verschachtelt:** ``NVT_7101/01.jpg``
* SHA-256 pro Foto berechnen (Duplikat-Erkennung)
* EXIF lesen (GPS, DateTimeOriginal)
* Fotos in ``data/projects/{project_id}/input/{sha256_prefix}/{basename}`` ablegen
* NVT-Hinweise aus Ordner-/Dateinamen extrahieren (die eigentliche
  Auswahl trifft ``app.classification.nvt_detector``)

Keine DB-Zugriffe, kein OCR, kein Vision — das Modul ist reines
Dateisystem + Metadaten.
"""

from __future__ import annotations

import hashlib
import io
import re
import shutil
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import GPSTAGS, TAGS

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

SUPPORTED_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"})

# NVT-Nummer aus Dateinamen/Ordnernamen. Bewusst strenger als der OCR-Regex:
# hier verlangen wir ein NVT-Prefix mit Trennzeichen, damit z.B. "20210812.jpg"
# nicht als "NVT 2021" fehlinterpretiert wird.
_PATH_NVT_RE = re.compile(r"(?:^|[_\-\s])NVT[_\-\s]?([0-9]{3,5}[A-Za-z]?)", re.IGNORECASE)


class IngestError(Exception):
    """Fehler bei Upload-Ingest (kaputtes ZIP, unzulässiger Pfad, …)."""


@dataclass(slots=True)
class IngestedPhoto:
    """Metadaten eines erfolgreich abgelegten Fotos."""

    original_filename: str
    relative_path: str  # Herkunft im Upload (ZIP-Pfad oder Ordner-Relativpfad)
    stored_path: Path
    mime_type: str
    width: int
    height: int
    sha256: str
    exif: dict[str, str] = field(default_factory=dict)
    exif_gps_lat: Decimal | None = None
    exif_gps_lon: Decimal | None = None
    exif_captured_at: datetime | None = None
    folder_nvt_hint: str | None = None
    filename_nvt_hint: str | None = None
    is_duplicate: bool = False  # True, wenn sha256 bereits bekannt war


# ---------------------------------------------------------------------------
# Öffentliche Einstiegspunkte
# ---------------------------------------------------------------------------


def ingest_bytes_as_zip(
    zip_bytes: bytes,
    *,
    project_id: UUID,
    storage_root: Path,
    known_sha256: set[str] | None = None,
) -> list[IngestedPhoto]:
    """Nimmt ein ZIP als Bytes entgegen und ingested alle darin enthaltenen Fotos."""
    with io.BytesIO(zip_bytes) as buf:
        try:
            with zipfile.ZipFile(buf) as zf:
                items = _iterate_zip(zf)
                return list(
                    _ingest_iterator(
                        items,
                        project_id=project_id,
                        storage_root=storage_root,
                        known_sha256=known_sha256 or set(),
                    )
                )
        except zipfile.BadZipFile as exc:
            raise IngestError(f"Kein gültiges ZIP: {exc}") from exc


def ingest_directory(
    directory: Path,
    *,
    project_id: UUID,
    storage_root: Path,
    known_sha256: set[str] | None = None,
) -> list[IngestedPhoto]:
    """Scannt einen Ordner-Tree rekursiv und ingested alle Fotos."""
    if not directory.is_dir():
        raise IngestError(f"Kein Verzeichnis: {directory}")
    items = _iterate_directory(directory)
    return list(
        _ingest_iterator(
            items,
            project_id=project_id,
            storage_root=storage_root,
            known_sha256=known_sha256 or set(),
        )
    )


def ingest_files(
    files: Iterable[tuple[str, bytes]],
    *,
    project_id: UUID,
    storage_root: Path,
    known_sha256: set[str] | None = None,
) -> list[IngestedPhoto]:
    """Ingested eine Sequenz (relative_path, bytes) — z.B. direkte Multipart-Uploads."""
    return list(
        _ingest_iterator(
            iter(files),
            project_id=project_id,
            storage_root=storage_root,
            known_sha256=known_sha256 or set(),
        )
    )


# ---------------------------------------------------------------------------
# Iteratoren über Quelle
# ---------------------------------------------------------------------------


def _iterate_zip(zf: zipfile.ZipFile) -> Iterator[tuple[str, bytes]]:
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename
        # Zip-Slip-Schutz: keine absoluten Pfade, keine ..-Segmente
        pure = PurePosixPath(name)
        if pure.is_absolute() or any(part == ".." for part in pure.parts):
            raise IngestError(f"Unerlaubter Pfad im ZIP: {name}")
        if not _is_supported_image_ext(name):
            continue
        # macOS-Rauschordner überspringen
        if any(part.startswith("__MACOSX") or part == ".DS_Store" for part in pure.parts):
            continue
        with zf.open(info) as fh:
            yield name, fh.read()


def _iterate_directory(directory: Path) -> Iterator[tuple[str, bytes]]:
    base = directory.resolve()
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if not _is_supported_image_ext(path.name):
            continue
        rel = path.resolve().relative_to(base).as_posix()
        yield rel, path.read_bytes()


# ---------------------------------------------------------------------------
# Kern: normalisieren + speichern
# ---------------------------------------------------------------------------


def _ingest_iterator(
    items: Iterator[tuple[str, bytes]],
    *,
    project_id: UUID,
    storage_root: Path,
    known_sha256: set[str],
) -> Iterator[IngestedPhoto]:
    project_dir = storage_root / "projects" / str(project_id) / "input"
    project_dir.mkdir(parents=True, exist_ok=True)
    seen_in_batch: set[str] = set()

    for relative_path, blob in items:
        try:
            photo = _process_single(
                relative_path=relative_path,
                blob=blob,
                project_dir=project_dir,
                known_sha256=known_sha256 | seen_in_batch,
            )
        except (UnidentifiedImageError, OSError):
            # Kaputtes Bild → überspringen (Rest des Uploads darf durchlaufen)
            continue
        seen_in_batch.add(photo.sha256)
        yield photo


def _process_single(
    *,
    relative_path: str,
    blob: bytes,
    project_dir: Path,
    known_sha256: set[str],
) -> IngestedPhoto:
    sha256 = hashlib.sha256(blob).hexdigest()
    is_duplicate = sha256 in known_sha256

    with Image.open(io.BytesIO(blob)) as im:
        im.load()
        width, height = im.size
        mime_type = _mime_for_image(im)
        exif_raw = _read_exif(im)

    exif_normalized, gps_lat, gps_lon, captured_at = _split_exif(exif_raw)

    basename = Path(relative_path).name
    parent_parts = PurePosixPath(relative_path).parts[:-1]

    folder_hint = _first_nvt_hint(parent_parts)
    filename_hint = _first_nvt_hint([basename])

    # Storage: data/projects/{pid}/input/{sha256[:2]}/{sha256[2:4]}/{sha256}.{ext}
    ext = Path(basename).suffix.lower() or ".jpg"
    stored_path = project_dir / sha256[:2] / sha256[2:4] / f"{sha256}{ext}"

    if not stored_path.exists():
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        # Bytes 1:1 speichern (kein Re-Encode → EXIF bleibt erhalten)
        with stored_path.open("wb") as fh:
            fh.write(blob)

    return IngestedPhoto(
        original_filename=basename,
        relative_path=relative_path,
        stored_path=stored_path,
        mime_type=mime_type,
        width=width,
        height=height,
        sha256=sha256,
        exif=exif_normalized,
        exif_gps_lat=gps_lat,
        exif_gps_lon=gps_lon,
        exif_captured_at=captured_at,
        folder_nvt_hint=folder_hint,
        filename_nvt_hint=filename_hint,
        is_duplicate=is_duplicate,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_supported_image_ext(name: str) -> bool:
    return Path(name).suffix.lower() in SUPPORTED_IMAGE_EXTS


def _mime_for_image(im: Image.Image) -> str:
    fmt = (im.format or "").upper()
    return {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "TIFF": "image/tiff",
        "WEBP": "image/webp",
    }.get(fmt, "application/octet-stream")


def _read_exif(im: Image.Image) -> dict[str, object]:
    try:
        raw = im._getexif()  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return {}
    if not raw:
        return {}
    result: dict[str, object] = {}
    for tag_id, value in raw.items():
        name = TAGS.get(tag_id, str(tag_id))
        if name == "GPSInfo" and isinstance(value, dict):
            result[name] = {GPSTAGS.get(k, str(k)): v for k, v in value.items()}
        else:
            result[name] = value
    return result


def _split_exif(
    exif: dict[str, object],
) -> tuple[dict[str, str], Decimal | None, Decimal | None, datetime | None]:
    """Serialisierbare Werte + geparste GPS/Datum."""
    normalized: dict[str, str] = {}
    for key, value in exif.items():
        if key == "GPSInfo":
            continue
        try:
            normalized[str(key)] = str(value)
        except Exception:
            continue

    gps_lat, gps_lon = _extract_gps(exif.get("GPSInfo"))
    captured_at = _extract_datetime(exif)
    return normalized, gps_lat, gps_lon, captured_at


def _extract_gps(gps_info: object) -> tuple[Decimal | None, Decimal | None]:
    if not isinstance(gps_info, dict):
        return None, None
    try:
        lat_raw = gps_info.get("GPSLatitude")
        lat_ref = str(gps_info.get("GPSLatitudeRef", "N")).upper()
        lon_raw = gps_info.get("GPSLongitude")
        lon_ref = str(gps_info.get("GPSLongitudeRef", "E")).upper()
    except AttributeError:
        return None, None
    lat = _dms_to_decimal(lat_raw)
    lon = _dms_to_decimal(lon_raw)
    if lat is not None and lat_ref == "S":
        lat = -lat
    if lon is not None and lon_ref == "W":
        lon = -lon
    return lat, lon


def _dms_to_decimal(value: object) -> Decimal | None:
    if not value:
        return None
    try:
        d, m, s = value  # type: ignore[misc]
        d_dec = _to_decimal(d)
        m_dec = _to_decimal(m)
        s_dec = _to_decimal(s)
        if d_dec is None or m_dec is None or s_dec is None:
            return None
        return d_dec + m_dec / Decimal(60) + s_dec / Decimal(3600)
    except (TypeError, ValueError):
        return None


def _to_decimal(x: object) -> Decimal | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return Decimal(str(x))
    if isinstance(x, Decimal):
        return x
    # PIL Rational: hat numerator/denominator
    num = getattr(x, "numerator", None)
    den = getattr(x, "denominator", None)
    if num is not None and den:
        try:
            return Decimal(num) / Decimal(den)
        except (InvalidOperation, ZeroDivisionError):
            return None
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return None


def _extract_datetime(exif: dict[str, object]) -> datetime | None:
    for key in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
        val = exif.get(key)
        if not val:
            continue
        text = str(val).strip()
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def _first_nvt_hint(parts: Iterable[str]) -> str | None:
    """Erste NVT-Nummer aus einer Pfad-Komponentenliste (Ordner oder Dateiname)."""
    for part in parts:
        m = _PATH_NVT_RE.search(part)
        if m:
            return m.group(1).upper()
    return None


# Für Tests
def cleanup_project_dir(storage_root: Path, project_id: UUID) -> None:
    """Löscht das Input-Verzeichnis eines Projekts vollständig. Nur für Tests."""
    target = storage_root / "projects" / str(project_id) / "input"
    if target.exists():
        shutil.rmtree(target)
