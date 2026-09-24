"""Erzeugt einfache Symbol-Grafiken für die Absicherungs-Visualisierung.

Ausgabe: PNG-Dateien unter ``data/symbols/`` mit Transparenz. Symbole sind
bewusst schematisch (rot/weiß gestreifte Baken, gelbe Warnleuchte); es geht
um technische Wiedererkennbarkeit, nicht um Foto-Realismus.

Neu erzeugen: ``python scripts/generate_symbols.py [--force]``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from app.config import get_settings  # noqa: E402

# ---------------------------------------------------------------------------
# Farb-Konstanten
# ---------------------------------------------------------------------------
RED = (204, 0, 0, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
YELLOW = (255, 200, 0, 255)
BLUE = (0, 78, 152, 255)
BLUE_SIGN = (0, 55, 128, 255)
TRANSPARENT = (0, 0, 0, 0)


def _new_canvas(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", size, TRANSPARENT)
    return img, ImageDraw.Draw(img)


def leitbake(size: tuple[int, int] = (60, 180)) -> Image.Image:
    """Weiß-rot gestreifte Leitbake mit gelber Warnleuchte oben."""
    img, d = _new_canvas(size)
    w, h = size
    body_top = 24
    body = (2, body_top, w - 2, h - 2)
    d.rectangle(body, fill=WHITE, outline=BLACK, width=1)

    stripe_h = (h - body_top - 2) // 6
    for i in range(6):
        y0 = body_top + i * stripe_h
        y1 = y0 + stripe_h
        if i % 2 == 0:
            # Schräge rote Streifen
            poly = [(2, y0), (w - 2, y0 + stripe_h // 3),
                    (w - 2, y1), (2, y1 - stripe_h // 3)]
            d.polygon(poly, fill=RED)

    # Warnleuchte oben
    d.ellipse((w // 2 - 12, 2, w // 2 + 12, 24), fill=YELLOW, outline=BLACK, width=1)
    return img


def warnbake(size: tuple[int, int] = (60, 220)) -> Image.Image:
    """Höhere Warnbake mit deutlicherer Signalleuchte."""
    return leitbake(size)  # visuelle Variante — für unser Word reicht die Bake


def absperrschranke(size: tuple[int, int] = (200, 90)) -> Image.Image:
    """Absperrschranke — horizontales rot-weiß gestreiftes Brett."""
    img, d = _new_canvas(size)
    w, h = size
    # Zwei Stützen
    d.rectangle((10, h - 30, 24, h - 2), fill=BLACK)
    d.rectangle((w - 24, h - 30, w - 10, h - 2), fill=BLACK)
    # Brett
    top = 15
    board = (5, top, w - 5, h - 35)
    d.rectangle(board, fill=WHITE, outline=BLACK, width=1)
    stripe_w = (w - 10) // 6
    for i in range(6):
        if i % 2 == 0:
            x0 = 5 + i * stripe_w
            d.rectangle((x0, top, x0 + stripe_w, h - 35), fill=RED)
    return img


def absperrgitter(size: tuple[int, int] = (200, 110)) -> Image.Image:
    """Bauzaun-Segment."""
    img, d = _new_canvas(size)
    w, h = size
    # Rahmen
    frame = (5, 15, w - 5, h - 5)
    d.rectangle(frame, outline=BLACK, width=3)
    # Vertikale Streben
    for x in range(20, w - 5, 15):
        d.line([(x, 15), (x, h - 5)], fill=BLACK, width=2)
    # Diagonale
    d.line([(5, 15), (w - 5, h - 5)], fill=BLACK, width=2)
    d.line([(5, h - 5), (w - 5, 15)], fill=BLACK, width=2)
    return img


def z123(size: tuple[int, int] = (140, 140)) -> Image.Image:
    """Verkehrszeichen Z 123 „Arbeitsstelle"."""
    img, d = _new_canvas(size)
    w, h = size
    # Rotes Dreieck
    d.polygon([(w // 2, 6), (w - 6, h - 6), (6, h - 6)], fill=WHITE, outline=RED)
    d.polygon([(w // 2, 6), (w - 6, h - 6), (6, h - 6)], outline=RED)
    for offset in range(6):
        d.polygon(
            [(w // 2, 6 + offset), (w - 6 - offset, h - 6 - offset), (6 + offset, h - 6 - offset)],
            outline=RED,
        )
    # Vereinfachtes Bauarbeiter-Symbol in der Mitte
    d.rectangle((w // 2 - 6, 55, w // 2 + 6, 70), fill=BLACK)  # Körper
    d.ellipse((w // 2 - 10, 40, w // 2 + 10, 60), fill=BLACK)  # Kopf
    d.line([(w // 2 + 6, 60), (w // 2 + 25, 45)], fill=BLACK, width=3)  # Arm mit Schaufel
    return img


def z283(size: tuple[int, int] = (120, 120)) -> Image.Image:
    """Verkehrszeichen Z 283 „Absolutes Haltverbot"."""
    img, d = _new_canvas(size)
    w, h = size
    # Rotes Kreis-Symbol mit blauem Kern
    d.ellipse((6, 6, w - 6, h - 6), fill=BLUE_SIGN, outline=RED, width=6)
    # Zwei diagonale rote Linien
    d.line([(20, 20), (w - 20, h - 20)], fill=RED, width=6)
    d.line([(w - 20, 20), (20, h - 20)], fill=RED, width=6)
    return img


def z286(size: tuple[int, int] = (120, 120)) -> Image.Image:
    """Verkehrszeichen Z 286 „Eingeschränktes Haltverbot"."""
    img, d = _new_canvas(size)
    w, h = size
    d.ellipse((6, 6, w - 6, h - 6), fill=BLUE_SIGN, outline=RED, width=6)
    d.line([(20, 20), (w - 20, h - 20)], fill=RED, width=6)
    return img


def haltverbot(size: tuple[int, int] = (120, 120)) -> Image.Image:
    """Alias auf Z 283 (absolutes Haltverbot)."""
    return z283(size)


def arrow(size: tuple[int, int] = (200, 60)) -> Image.Image:
    """Roter Richtungspfeil (nach rechts)."""
    img, d = _new_canvas(size)
    w, h = size
    body_h = h // 3
    body_y = (h - body_h) // 2
    d.rectangle((0, body_y, w - 60, body_y + body_h), fill=RED)
    d.polygon([(w - 60, 5), (w - 5, h // 2), (w - 60, h - 5)], fill=RED)
    return img


def text_marker(size: tuple[int, int] = (240, 60)) -> Image.Image:
    """Weißes Text-Label mit schwarzem Rand."""
    img, d = _new_canvas(size)
    w, h = size
    d.rectangle((2, 2, w - 2, h - 2), fill=WHITE, outline=BLACK, width=2)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    d.text((10, 15), "Label", fill=BLACK, font=font)
    return img


SYMBOLS: dict[str, callable] = {
    "leitbake": leitbake,
    "warnbake": warnbake,
    "absperrschranke": absperrschranke,
    "absperrgitter": absperrgitter,
    "z_123": z123,
    "z_283": z283,
    "z_286": z286,
    "haltverbot": haltverbot,
    "arrow": arrow,
    "text": text_marker,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Bestehende überschreiben")
    args = parser.parse_args()

    settings = get_settings()
    out_dir = settings.storage_path / "symbols"
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    for name, factory in SYMBOLS.items():
        target = out_dir / f"{name}.png"
        if target.exists() and not args.force:
            print(f"  [skip]  {target}")
            skipped += 1
            continue
        img = factory()
        img.save(target, "PNG")
        print(f"  [write] {target}")
        written += 1

    print(f"\n{written} Symbole geschrieben, {skipped} übersprungen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
