"""Rendert das Overlay-Modell (Symbols + Shapes) auf ein Basis-Foto.

Original bleibt unverändert (Master-Prompt §14 / Build-Prompt §78) — es wird
eine neue Datei ``proposal.jpg`` erzeugt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw

from app.core.enums import OverlaySymbolType
from app.core.schemas import (
    OverlayPointSchema,
    OverlayShapeSchema,
    OverlaySymbolSchema,
    VisualizationSchema,
)
from app.visualization.symbols import SymbolRegistry, get_symbol_registry


class RenderError(Exception):
    """Wird geworfen, wenn das Rendering scheitert (fehlendes Foto etc.)."""


@dataclass
class RenderResult:
    output_path: Path
    width: int
    height: int
    rendered_symbol_count: int = 0
    rendered_shape_count: int = 0
    warnings: list[str] = field(default_factory=list)


# Farb-Konstanten (RGBA)
_BARRIER_RED = (204, 0, 0, 220)
_BARRIER_OUTLINE = (150, 0, 0, 255)
_BULLI_YELLOW = (255, 200, 0, 140)
_BULLI_OUTLINE = (200, 140, 0, 255)


def _abs(pt: OverlayPointSchema, w: int, h: int) -> tuple[int, int]:
    return int(float(pt.x) * w), int(float(pt.y) * h)


def _draw_shape(
    draw: ImageDraw.ImageDraw,
    shape: OverlayShapeSchema,
    w: int,
    h: int,
    is_bulli: bool,
) -> None:
    fill = _BULLI_YELLOW if is_bulli else _BARRIER_RED
    outline = _BULLI_OUTLINE if is_bulli else _BARRIER_OUTLINE
    coords = [_abs(p, w, h) for p in shape.points]

    if shape.kind == "line":
        draw.line(coords, fill=outline, width=6)
        return
    if shape.kind == "rect" and len(coords) >= 2:
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        draw.rectangle(rect, fill=fill, outline=outline, width=4)
        return
    # polygon
    draw.polygon(coords, fill=fill, outline=outline)
    # Umriss verdicken (Pillow zeichnet dünn)
    draw.line(coords + [coords[0]], fill=outline, width=5)


def _paste_symbol(
    canvas: Image.Image,
    symbol: OverlaySymbolSchema,
    registry: SymbolRegistry,
    warnings: list[str],
) -> bool:
    try:
        img = registry.load(OverlaySymbolType(symbol.type))
    except FileNotFoundError as exc:
        warnings.append(str(exc))
        return False

    scale = max(0.1, float(symbol.scale))
    # Basisgröße relativ zur Bildhöhe: ein Symbol soll ~12 % der Bildhöhe belegen
    target_h = int(canvas.height * 0.18 * scale)
    ratio = target_h / img.height
    target_w = max(1, int(img.width * ratio))
    scaled = img.resize((target_w, target_h), Image.LANCZOS)

    if float(symbol.rotation) != 0:
        scaled = scaled.rotate(float(symbol.rotation), expand=True)

    cx = int(float(symbol.x) * canvas.width)
    cy = int(float(symbol.y) * canvas.height)
    x = cx - scaled.width // 2
    y = cy - scaled.height // 2

    canvas.alpha_composite(scaled, dest=(x, y))
    return True


def render_overlay(
    *,
    base_photo_path: Path,
    visualization: VisualizationSchema,
    output_path: Path,
    registry: SymbolRegistry | None = None,
    quality: int = 88,
) -> RenderResult:
    """Legt Absperrung + Symbole auf ein Basis-Foto und speichert als JPEG."""
    if not base_photo_path.is_file():
        raise RenderError(f"Basis-Foto fehlt: {base_photo_path}")

    reg = registry or get_symbol_registry()
    warnings: list[str] = []

    try:
        base = Image.open(base_photo_path).convert("RGBA")
    except Exception as exc:
        raise RenderError(f"Foto nicht lesbar: {exc}") from exc

    w, h = base.size
    overlay_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_layer)

    # Zuerst Bulli-Rechteck (heuristisch: einziges Shape mit kind="rect")
    shapes_sorted = sorted(visualization.shapes, key=lambda s: 0 if s.kind == "rect" else 1)
    for shape in shapes_sorted:
        _draw_shape(draw, shape, w, h, is_bulli=(shape.kind == "rect"))

    canvas = Image.alpha_composite(base, overlay_layer)

    rendered_symbols = 0
    for sym in visualization.symbols:
        if _paste_symbol(canvas, sym, reg, warnings):
            rendered_symbols += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(str(output_path), "JPEG", quality=quality)

    return RenderResult(
        output_path=output_path,
        width=w,
        height=h,
        rendered_symbol_count=rendered_symbols,
        rendered_shape_count=len(visualization.shapes),
        warnings=warnings,
    )
