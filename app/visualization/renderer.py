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
_BARRIER_RED = (204, 0, 0, 220)
_BARRIER_OUTLINE = (150, 0, 0, 255)
_BULLI_YELLOW = (255, 200, 0, 140)
_BULLI_OUTLINE = (200, 140, 0, 255)

# Absperrung: rot-weiße "Flatterband"-Streifen statt einer dünnen Linie,
# damit die Absperrung im Foto klar als solche erkennbar ist.
_BARRIER_STRIPE_RED = (204, 0, 0, 255)
_BARRIER_STRIPE_WHITE = (255, 255, 255, 255)
_BARRIER_STRIPE_WIDTH = 14
_BARRIER_STRIPE_LEN = 16
_BARRIER_POST = (60, 60, 60, 255)

# Bulli als einfache 3D-Box (Vorderfläche + Dach + zwei Seitenflächen), damit
# erkennbar ist, dass ein Fahrzeug auf der Fläche steht (kein echtes 3D-Modell,
# nur eine schattierte Quader-Näherung in Bild-Koordinaten).
_BULLI_FRONT = (255, 200, 0, 235)
_BULLI_TOP = (255, 226, 140, 220)
_BULLI_SIDE = (176, 124, 0, 220)
_BULLI_EDGE = (110, 74, 0, 255)

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


def _draw_barrier_line(draw: ImageDraw.ImageDraw, coords: list[tuple[int, int]]) -> None:
    """Zeichnet eine Absperrung als rot-weiß gestreiftes Flatterband mit
    Pfosten an den Endpunkten — deutlich erkennbar, auch vor unruhigem
    Hintergrund (Hecke, Schatten etc.)."""
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if length < 1:
            continue
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        steps = max(1, int(length // _BARRIER_STRIPE_LEN))
        for i in range(steps):
            t0 = i * length / steps
            t1 = (i + 1) * length / steps
            seg = [(x0 + ux * t0, y0 + uy * t0), (x0 + ux * t1, y0 + uy * t1)]
            color = _BARRIER_STRIPE_RED if i % 2 == 0 else _BARRIER_STRIPE_WHITE
            draw.line(seg, fill=color, width=_BARRIER_STRIPE_WIDTH)
    for x, y in (coords[0], coords[-1]):
        r = _BARRIER_STRIPE_WIDTH // 2 + 3
        draw.ellipse([x - r, y - r, x + r, y + r], fill=_BARRIER_POST)


def _draw_bulli_box3d(
    draw: ImageDraw.ImageDraw,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    canvas_h: int,
) -> None:
    """Zeichnet die Bulli-Standfläche als schattierten Quader (Front, Dach,
    zwei Seiten-Keile) statt als flaches Rechteck, damit erkennbar ist, dass
    dort ein Fahrzeug steht. Keine echte 3D-Rekonstruktion — die Vorderkante
    (``bottom_right``-Fläche) bestimmt Breite/Höhe des Fahrzeugs, die Tiefe
    (Dach-Versatz) ist proportional zur Breite, nicht an die (oft sehr weit
    entfernte) Rückkante des Eingabe-Rechtecks gekoppelt, damit die Box
    kompakt bleibt statt turmartig in die Länge gezogen zu wirken."""
    x0, y0 = top_left       # nur zur Ordnung genutzt, nicht als Fahrzeug-Rückkante
    x1, y1 = bottom_right   # Bodenkontakt vorne (Referenz für Breite/Höhe)
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    front_w = x1 - x0
    height = max(8, int(canvas_h * 0.10 * _perspective_factor(y1 / canvas_h)))
    depth = max(6, int(front_w * 0.35))
    shrink = front_w * 0.12

    front_bl, front_br = (x0, y1), (x1, y1)
    front_tl, front_tr = (x0, y1 - height), (x1, y1 - height)
    back_tl = (x0 + shrink, y1 - height - depth)
    back_tr = (x1 - shrink, y1 - height - depth)

    # Seiten-Keile zuerst (dunkler, wirken wie Schattierung), dann Dach,
    # dann Front zuletzt (am stärksten sichtbar).
    draw.polygon([front_bl, front_tl, back_tl], fill=_BULLI_SIDE, outline=_BULLI_EDGE)
    draw.polygon([front_br, front_tr, back_tr], fill=_BULLI_SIDE, outline=_BULLI_EDGE)
    draw.polygon([front_tl, back_tl, back_tr, front_tr], fill=_BULLI_TOP, outline=_BULLI_EDGE)
    draw.polygon([front_bl, front_br, front_tr, front_tl], fill=_BULLI_FRONT, outline=_BULLI_EDGE)


def _draw_shape(
    draw: ImageDraw.ImageDraw,
    shape: OverlayShapeSchema,
    w: int,
    h: int,
    is_bulli: bool,
) -> None:
    """Bulli-Fläche als schattierter Quader (siehe ``_draw_bulli_box3d``),
    Absperrbereich als rot-weißes Flatterband (siehe ``_draw_barrier_line``) —
    keine flächige Rot-Füllung, die Absperrung markiert die Grenze, nicht
    eine gesperrte Fläche."""
    coords = [_abs(p, w, h) for p in shape.points]

    if is_bulli and shape.kind == "rect" and len(coords) >= 2:
        _draw_bulli_box3d(draw, coords[0], coords[1], h)
        return
    if shape.kind == "line":
        _draw_barrier_line(draw, coords)
        return
    if shape.kind == "rect" and len(coords) >= 2:
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        draw.rectangle(rect, outline=_BARRIER_OUTLINE, width=4)
        return
    # polygon (Absperrbereich): als Flatterband-Umriss, keine Füllung
    _draw_barrier_line(draw, coords + [coords[0]])


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

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 8
    box = (cx - text_w // 2 - pad, cy - text_h // 2 - pad, cx + text_w // 2 + pad, cy + text_h // 2 + pad)

    draw.rectangle(box, fill=(255, 255, 255, 235), outline=(0, 0, 0, 255), width=2)
    draw.text((cx - text_w // 2 - bbox[0], cy - text_h // 2 - bbox[1]), text, fill=(0, 0, 0, 255), font=font)


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

    # Zuerst Bulli-Rechteck (heuristisch: einziges Shape mit kind="rect")
    shapes_sorted = sorted(visualization.shapes, key=lambda s: 0 if s.kind == "rect" else 1)
    for shape in shapes_sorted:
        _draw_shape(draw, shape, w, h, is_bulli=(shape.kind == "rect"))

    canvas = Image.alpha_composite(base, overlay_layer)

    rendered_symbols = 0
    for sym in visualization.symbols:
        if sym.type == OverlaySymbolType.TEXT and sym.label:
            _draw_text_label(canvas, sym)
            rendered_symbols += 1
        elif _paste_symbol(canvas, sym, reg, warnings):
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
