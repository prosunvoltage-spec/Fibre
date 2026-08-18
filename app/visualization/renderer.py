"""Rendert das Overlay-Modell (Symbols + Shapes) auf ein Basis-Foto.

Original bleibt unverändert (Master-Prompt §14 / Build-Prompt §78) — es wird
eine neue Datei ``proposal.jpg`` erzeugt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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
_BARRIER_OUTLINE = (150, 0, 0, 255)

# Absperrkante: kräftige durchgezogene rote Linie wie in den freigegebenen
# Referenz-VRA (Roxel S. 3–52). Die Linienbreite skaliert perspektivisch mit
# der Bildhöhe, damit nahe Abschnitte dicker wirken als ferne.
_BARRIER_RED = (227, 27, 35, 255)
_BARRIER_WIDTH_NEAR = 13
_BARRIER_WIDTH_FAR = 7

# Perspektivische Näherung (kein echtes 3D/keine Kamera-Kalibrierung):
# Symbole weiter oben im Bild (kleineres y, "ferner") werden kleiner
# gezeichnet, Symbole weiter unten ("näher") größer. Linear interpoliert.
_PERSPECTIVE_MIN_SCALE = 0.55  # bei y=0.0 (oberer Bildrand)
_PERSPECTIVE_MAX_SCALE = 1.15  # bei y=1.0 (unterer Bildrand)


def _perspective_factor(y: float) -> float:
    y = max(0.0, min(1.0, y))
    return _PERSPECTIVE_MIN_SCALE + (_PERSPECTIVE_MAX_SCALE - _PERSPECTIVE_MIN_SCALE) * y


def _abs(pt: OverlayPointSchema, w: int, h: int) -> tuple[int, int]:
    return int(float(pt.x) * w), int(float(pt.y) * h)


def _draw_barrier_line(
    draw: ImageDraw.ImageDraw, coords: list[tuple[int, int]], canvas_h: int
) -> None:
    """Zeichnet die Absperrkante als durchgezogene rote Linie, wie in den
    freigegebenen Referenz-VRA.

    Die Linie liegt in der Bodenebene: jedes Teilstück wird entsprechend
    seiner Bildhöhe skaliert (nah = dicker, fern = dünner), und die Ecken
    werden mit Kreisen gefüllt, damit der Polygonzug an den Knicken nicht
    aufreißt. Das erzeugt die räumliche Wirkung ohne Kamera-Kalibrierung."""
    def width_at(y: int) -> int:
        t = _perspective_factor(y / canvas_h)
        span = _PERSPECTIVE_MAX_SCALE - _PERSPECTIVE_MIN_SCALE
        frac = (t - _PERSPECTIVE_MIN_SCALE) / span if span else 0.5
        return max(2, int(_BARRIER_WIDTH_FAR + (_BARRIER_WIDTH_NEAR - _BARRIER_WIDTH_FAR) * frac))

    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        draw.line([(x0, y0), (x1, y1)], fill=_BARRIER_RED, width=width_at((y0 + y1) // 2))
    for x, y in coords:
        r = width_at(y) // 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=_BARRIER_RED)


def _draw_shape(
    draw: ImageDraw.ImageDraw,
    shape: OverlayShapeSchema,
    w: int,
    h: int,
    is_bulli: bool,
) -> None:
    """Zeichnet die Absperrkante. Flächen werden nie gefüllt — die Absperrung
    markiert eine Grenze, keinen eingefärbten Bereich (so auch in allen
    Referenz-VRA). ``rect``-Shapes werden als geschlossener Kantenzug
    gezeichnet, ``polygon`` ebenfalls geschlossen, ``line`` offen."""
    coords = [_abs(p, w, h) for p in shape.points]

    if shape.kind == "line":
        _draw_barrier_line(draw, coords, h)
        return
    if shape.kind == "rect" and len(coords) >= 2:
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        _draw_barrier_line(draw, rect, h)
        return
    _draw_barrier_line(draw, coords + [coords[0]], h)


_TEXT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _draw_text_label(canvas: Image.Image, symbol: OverlaySymbolSchema) -> None:
    """Zeichnet eine Textbox (z.B. 'Regelplan: VZP1') an normalisierter Position."""
    draw = ImageDraw.Draw(canvas)
    try:
        font_size = max(14, int(canvas.height * 0.03 * float(symbol.scale)))
        font = ImageFont.truetype(_TEXT_FONT_PATH, font_size)
    except OSError:
        font = ImageFont.load_default()

    text = symbol.label or ""
    cx = int(float(symbol.x) * canvas.width)
    cy = int(float(symbol.y) * canvas.height)

    # multiline_textbbox deckt auch einzeilige Labels korrekt ab
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4, align="center")
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 8
    box = (cx - text_w // 2 - pad, cy - text_h // 2 - pad, cx + text_w // 2 + pad, cy + text_h // 2 + pad)

    draw.rectangle(box, fill=(255, 255, 255, 235), outline=(0, 0, 0, 255), width=2)
    draw.multiline_text(
        (cx - text_w // 2 - bbox[0], cy - text_h // 2 - bbox[1]),
        text, fill=(0, 0, 0, 255), font=font, spacing=4, align="center",
    )


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
    persp = _perspective_factor(float(symbol.y))
    # Basisgröße relativ zur Bildhöhe (~18%), perspektivisch skaliert:
    # Symbole weiter oben im Bild (ferner) werden kleiner gezeichnet.
    target_h = max(1, int(canvas.height * 0.18 * scale * persp))
    ratio = target_h / img.height
    target_w = max(1, int(img.width * ratio))
    scaled = img.resize((target_w, target_h), Image.LANCZOS)

    if float(symbol.rotation) != 0:
        scaled = scaled.rotate(float(symbol.rotation), expand=True)

    cx = int(float(symbol.x) * canvas.width)
    cy = int(float(symbol.y) * canvas.height)
    # Anker am unteren Rand (Bodenkontaktpunkt), nicht Bildmitte — passend
    # zur perspektivischen Skalierung (Objekt "steht" auf dem y-Punkt).
    x = cx - scaled.width // 2
    y = cy - scaled.height

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

    for shape in visualization.shapes:
        _draw_shape(draw, shape, w, h, is_bulli=False)

    canvas = Image.alpha_composite(base, overlay_layer)

    # Baken zuerst, Textlabels zuletzt — Labels sollen nie von einem Symbol
    # überdeckt werden (so auch in den Referenz-VRA).
    rendered_symbols = 0
    text_symbols = []
    for sym in visualization.symbols:
        if sym.type == OverlaySymbolType.TEXT and sym.label:
            text_symbols.append(sym)
        elif _paste_symbol(canvas, sym, reg, warnings):
            rendered_symbols += 1
    for sym in text_symbols:
        _draw_text_label(canvas, sym)
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
