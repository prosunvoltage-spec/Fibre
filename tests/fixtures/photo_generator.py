"""Utility-Funktionen für synthetische Test-Fotos.

Generiert JPGs mit optionalem Overlay-Text — reicht für Ingest-,
Detector- und Service-Tests. Für den Tesseract-Contract-Test wird
zusätzlich ein sehr großer, hochkontrastiger Text erzeugt, damit die
OCR ohne Trainingsdaten-Feintuning stabil liest.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_SIZE = (1200, 800)


@dataclass(frozen=True)
class PhotoSpec:
    """Beschreibt ein synthetisches Test-Foto."""

    filename: str  # relativer Pfad im ZIP (kann Unterordner enthalten)
    overlay_lines: list[str]
    size: tuple[int, int] = DEFAULT_SIZE
    seed_color: tuple[int, int, int] = (240, 240, 240)


def render_photo(spec: PhotoSpec) -> bytes:
    """Rendert ein Foto mit Overlay-Text als JPG."""
    im = Image.new("RGB", spec.size, spec.seed_color)
    draw = ImageDraw.Draw(im)
    font = _load_font()
    y = 40
    for line in spec.overlay_lines:
        draw.text((40, y), line, fill=(0, 0, 0), font=font)
        y += font.size + 12 if hasattr(font, "size") else 30
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def render_large_ocr_photo(text_lines: list[str], size: tuple[int, int] = (1800, 1200)) -> bytes:
    """Foto mit hochkontrastigem großen Text — für Tesseract-Contract-Tests."""
    im = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(im)
    font = _load_font(preferred_size=64)
    y = 60
    for line in text_lines:
        draw.text((60, y), line, fill=(0, 0, 0), font=font)
        y += (font.size if hasattr(font, "size") else 64) + 20
    buf = io.BytesIO()
    im.save(buf, "PNG")  # PNG statt JPEG: schärfere Kanten für OCR
    return buf.getvalue()


def build_zip_from_specs(specs: list[PhotoSpec]) -> bytes:
    """Baut ein ZIP mit den angegebenen Foto-Spezifikationen."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for spec in specs:
            zf.writestr(spec.filename, render_photo(spec))
    return buf.getvalue()


def write_directory_from_specs(base: Path, specs: list[PhotoSpec]) -> Path:
    """Legt Foto-Spezifikationen als Ordner-Tree ab."""
    for spec in specs:
        target = base / spec.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(render_photo(spec))
    return base


def _load_font(preferred_size: int = 22) -> ImageFont.ImageFont:
    """Nimmt einen TTF-Font wenn vorhanden, sonst Default (bitmap)."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=preferred_size)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Kanonische Fixture: 5 NVTs für den Phase-4-Abnahmetest
# ---------------------------------------------------------------------------


def canonical_five_nvt_specs() -> list[PhotoSpec]:
    """5 NVT-Fotos passend zum Abnahmekriterium PROJECT_PLAN.md §4 Phase 4."""
    return [
        PhotoSpec(
            filename="NVT_7101.jpg",
            overlay_lines=[
                "NVT 7101",
                "Hauptstrasse 12",
                "48161 Muenster",
                "13.08.2026 09:15",
            ],
        ),
        PhotoSpec(
            filename="NVT_7102.jpg",
            overlay_lines=[
                "NVT 7102",
                "Roxeler Strasse 42",
                "48161 Muenster",
                "13.08.2026 09:25",
            ],
        ),
        PhotoSpec(
            filename="NVT_7103.jpg",
            overlay_lines=[
                "NVT 7103",
                "Am Sandberg 5a",
                "48159 Muenster",
                "13.08.2026 09:40",
            ],
        ),
        PhotoSpec(
            filename="NVT_7104.jpg",
            overlay_lines=[
                "NVT 7104",
                "Muensterstrasse 88",
                "48161 Muenster",
                "13.08.2026 10:05",
            ],
        ),
        PhotoSpec(
            filename="NVT_7105.jpg",
            overlay_lines=[
                "NVT 7105",
                "Bahnhofsplatz 3",
                "48143 Muenster",
                "13.08.2026 10:20",
            ],
        ),
    ]
