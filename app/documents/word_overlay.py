"""Absperr-Overlay als **bewegliche** Word-Zeichenobjekte.

Der Renderer (``app/visualization/renderer.py``) brennt das Overlay in ein
JPEG. Für die Behördenabstimmung braucht der Fachanwender die Elemente aber
verschiebbar: Absperrkante, Leitbaken und Textfelder sollen in Word angefasst
und versetzt werden können, ohne das Bild neu zu rendern.

Dieses Modul legt deshalb das **unveränderte Originalfoto** als Inline-Bild ab
und setzt darüber frei positionierte DrawingML-Objekte (``wps:wsp`` für Linien
und Textfelder, ``pic:pic`` für Symbol-Grafiken). Alle sind in Word einzeln
anklick- und ziehbar.

Das Original bleibt unangetastet (Master-Prompt §14) — es wird nur eingebettet,
nicht überschrieben.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.shared import Emu
from docx.text.paragraph import Paragraph

from app.core.enums import OverlaySymbolType
from app.core.schemas import VisualizationSchema
from app.visualization.symbols import SymbolRegistry, get_symbol_registry

EMU_PER_PT = 12700

_BARRIER_HEX = "E31B23"      # gleiches Rot wie im gerenderten Overlay
_BARRIER_PT = 3.0            # Linienstärke der Absperrkante
_LABEL_FILL = "FFFFFF"
_LABEL_LINE = "000000"

# Symbolhöhe relativ zur Bildhöhe (entspricht der Renderer-Basisgröße)
_SYMBOL_H_FRAC = 0.18


@dataclass
class OverlayPlacement:
    """Position und Größe des Fotos im Dokument (EMU, relativ zur Spalte)."""

    width_emu: int
    height_emu: int


def _drawing_wrapper(inner: str, name: str, x_emu: int, y_emu: int,
                     cx_emu: int, cy_emu: int, z: int) -> str:
    """Gemeinsame Anchor-Hülle: frei positioniert, über dem Text, verschiebbar."""
    return f"""
<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
             distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="{z}"
             behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">
    <wp:simplePos x="0" y="0"/>
    <wp:positionH relativeFrom="column"><wp:posOffset>{x_emu}</wp:posOffset></wp:positionH>
    <wp:positionV relativeFrom="paragraph"><wp:posOffset>{y_emu}</wp:posOffset></wp:positionV>
    <wp:extent cx="{max(1, cx_emu)}" cy="{max(1, cy_emu)}"/>
    <wp:effectExtent l="0" t="0" r="0" b="0"/>
    <wp:wrapNone/>
    <wp:docPr id="{z}" name="{escape(name)}"/>
    {inner}
  </wp:anchor>
</w:drawing>"""


def _line_shape(x0: int, y0: int, x1: int, y1: int, z: int, name: str) -> str:
    """Gerade Linie als eigenständige, verschiebbare Form."""
    left, top = min(x0, x1), min(y0, y1)
    cx, cy = abs(x1 - x0), abs(y1 - y0)
    # Richtung über flipH/flipV kodieren (Bounding-Box ist immer achsparallel)
    flip_h = ' flipH="1"' if x1 < x0 else ""
    flip_v = ' flipV="1"' if y1 < y0 else ""
    inner = f"""
    <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
        <wps:wsp xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
          <wps:cNvCnPr/>
          <wps:spPr>
            <a:xfrm{flip_h}{flip_v}>
              <a:off x="0" y="0"/><a:ext cx="{max(1, cx)}" cy="{max(1, cy)}"/>
            </a:xfrm>
            <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
            <a:ln w="{int(_BARRIER_PT * EMU_PER_PT)}" cap="rnd">
              <a:solidFill><a:srgbClr val="{_BARRIER_HEX}"/></a:solidFill>
              <a:round/>
            </a:ln>
          </wps:spPr>
          <wps:bodyPr/>
        </wps:wsp>
      </a:graphicData>
    </a:graphic>"""
    return _drawing_wrapper(inner, name, left, top, cx, cy, z)


def _textbox_shape(text: str, x: int, y: int, cx: int, cy: int, z: int,
                   name: str, font_pt: float) -> str:
    """Weißes Textfeld mit schwarzem Rahmen — in Word editier- und verschiebbar."""
    lines = text.split("\n")
    paras = "".join(
        f'<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="0"/></w:pPr>'
        f'<w:r><w:rPr><w:b/><w:sz w:val="{int(font_pt * 2)}"/></w:rPr>'
        f"<w:t xml:space=\"preserve\">{escape(line)}</w:t></w:r></w:p>"
        for line in lines
    )
    inner = f"""
    <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
        <wps:wsp xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
          <wps:cNvSpPr txBox="1"/>
          <wps:spPr>
            <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
            <a:solidFill><a:srgbClr val="{_LABEL_FILL}"/></a:solidFill>
            <a:ln w="12700"><a:solidFill><a:srgbClr val="{_LABEL_LINE}"/></a:solidFill></a:ln>
          </wps:spPr>
          <wps:txbx>
            <w:txbxContent xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              {paras}
            </w:txbxContent>
          </wps:txbx>
          <wps:bodyPr rot="0" vert="horz" wrap="square" lIns="36000" tIns="18000"
                      rIns="36000" bIns="18000" anchor="ctr">
            <a:spAutoFit/>
          </wps:bodyPr>
        </wps:wsp>
      </a:graphicData>
    </a:graphic>"""
    return _drawing_wrapper(inner, name, x, y, cx, cy, z)


def _picture_shape(rel_id: str, pic_id: int, x: int, y: int, cx: int, cy: int,
                   z: int, name: str) -> str:
    """Symbol-Grafik (Leitbake etc.) als frei positioniertes Bild."""
    inner = f"""
    <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
        <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
          <pic:nvPicPr>
            <pic:cNvPr id="{pic_id}" name="{escape(name)}"/>
            <pic:cNvPicPr/>
          </pic:nvPicPr>
          <pic:blipFill>
            <a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                    r:embed="{rel_id}"/>
            <a:stretch><a:fillRect/></a:stretch>
          </pic:blipFill>
          <pic:spPr>
            <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          </pic:spPr>
        </pic:pic>
      </a:graphicData>
    </a:graphic>"""
    return _drawing_wrapper(inner, name, x, y, cx, cy, z)


def _append_drawing(paragraph: Paragraph, xml: str) -> None:
    from docx.oxml import parse_xml

    run = paragraph.add_run()
    run._r.append(parse_xml(xml))


def add_movable_overlay(
    doc: DocxDocument,
    paragraph: Paragraph,
    *,
    visualization: VisualizationSchema,
    placement: OverlayPlacement,
    registry: SymbolRegistry | None = None,
    z_base: int = 100,
) -> list[str]:
    """Setzt Absperrkante, Symbole und Textfelder als bewegliche Objekte über
    das zuvor in ``paragraph`` eingefügte Foto.

    ``placement`` beschreibt die Anzeigegröße des Fotos; alle normalisierten
    0–1-Koordinaten der Visualization werden darauf abgebildet. Rückgabe ist
    eine Liste von Warnungen (z.B. fehlende Symbol-Dateien).
    """
    reg = registry or get_symbol_registry()
    warnings: list[str] = []
    w, h = placement.width_emu, placement.height_emu
    # docPr-IDs müssen dokumentweit eindeutig sein, sonst verlangt Word beim
    # Öffnen eine Reparatur. Deshalb ein Zähler am Dokument statt pro Abschnitt.
    z = max(z_base, getattr(doc, _ID_COUNTER_ATTR, z_base))

    def ax(v) -> int:  # type: ignore[no-untyped-def]
        return int(float(v) * w)

    def ay(v) -> int:  # type: ignore[no-untyped-def]
        return int(float(v) * h)

    # --- Absperrkanten: jedes Segment als eigene, einzeln ziehbare Linie ---
    for si, shape in enumerate(visualization.shapes):
        pts = [(ax(p.x), ay(p.y)) for p in shape.points]
        if shape.kind == "rect" and len(pts) >= 2:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        elif shape.kind == "polygon":
            pts = pts + [pts[0]]
        for i, ((x0, y0), (x1, y1)) in enumerate(zip(pts, pts[1:])):
            z += 1
            _append_drawing(
                paragraph,
                _line_shape(x0, y0, x1, y1, z, f"Absperrkante {si + 1}.{i + 1}"),
            )

    # --- Symbole und Textfelder ---
    for sym in visualization.symbols:
        z += 1
        cx_, cy_ = ax(sym.x), ay(sym.y)

        if sym.type == OverlaySymbolType.TEXT and sym.label:
            lines = sym.label.split("\n")
            font_pt = max(7.0, 10.0 * float(sym.scale))
            box_w = int(max(len(ln) for ln in lines) * font_pt * 0.62 * EMU_PER_PT)
            box_h = int(len(lines) * font_pt * 1.7 * EMU_PER_PT)
            _append_drawing(
                paragraph,
                _textbox_shape(
                    sym.label, cx_ - box_w // 2, cy_ - box_h // 2,
                    box_w, box_h, z, f"Beschriftung: {lines[0][:30]}", font_pt,
                ),
            )
            continue

        try:
            img_path = reg.path_for(OverlaySymbolType(sym.type))
        except (FileNotFoundError, AttributeError):
            img_path = None
        if img_path is None or not Path(img_path).is_file():
            warnings.append(f"Symbol-Datei fehlt: {sym.type}")
            continue

        from PIL import Image

        with Image.open(img_path) as im:
            iw, ih = im.size
        sym_h = int(h * _SYMBOL_H_FRAC * max(0.1, float(sym.scale)))
        sym_w = int(sym_h * iw / ih)
        rel_id = _ensure_image_rel(doc, paragraph, Path(img_path))
        _append_drawing(
            paragraph,
            _picture_shape(
                rel_id, z, cx_ - sym_w // 2, cy_ - sym_h,  # Bodenanker wie im Renderer
                sym_w, sym_h, z, f"Symbol {sym.type}",
            ),
        )

    setattr(doc, _ID_COUNTER_ATTR, z + 1)
    return warnings


_REL_CACHE_ATTR = "_vra_symbol_rels"
_ID_COUNTER_ATTR = "_vra_shape_id"


def _ensure_image_rel(doc: DocxDocument, paragraph: Paragraph, path: Path) -> str:
    """Bettet eine Symbol-Grafik einmal pro Dokument ein und liefert die rId."""
    cache: dict[str, str] = getattr(doc, _REL_CACHE_ATTR, None) or {}
    key = str(path)
    if key in cache:
        return cache[key]
    part = paragraph.part
    rel_id, _ = part.get_or_add_image(str(path))
    cache[key] = rel_id
    setattr(doc, _REL_CACHE_ATTR, cache)
    return rel_id


def photo_placement(photo_path: Path, display_width_emu: int) -> OverlayPlacement:
    """Rechnet die Anzeigehöhe aus dem Seitenverhältnis des Fotos."""
    from PIL import Image

    with Image.open(photo_path) as im:
        iw, ih = im.size
    return OverlayPlacement(
        width_emu=display_width_emu,
        height_emu=int(display_width_emu * ih / iw),
    )
