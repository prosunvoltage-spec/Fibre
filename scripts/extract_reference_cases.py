"""Extrahiert Fotos + Regelpläne aus der Referenz-VRA-PDF.

Was passiert:
- Für jedes Referenzfall-Verzeichnis unter ``knowledge/referenzfaelle/NVT_*/``
  wird die ``source_page`` aus ``nvt.json`` gelesen und diese Seite als
  ``photo.png`` (nur der Foto-Bereich, ohne die Kopfleiste des PDF-Viewers)
  rendert.
- Für jeden Regelplan unter ``knowledge/regelplaene/*/`` wird die zugehörige
  ``source_page`` als ``plan.pdf`` (Einseiter) exportiert und zusätzlich als
  ``preview.png`` gerendert.
- ``extracted_at`` in jeder ``nvt.json`` wird aktualisiert; sonst wird KEIN
  Metadatenfeld verändert (Fachanwender-Pflege bleibt erhalten).

Aufruf:

    python scripts/extract_reference_cases.py --pdf PFAD/zur/Roxel.pdf

Optional:
    --nvt 7107          nur ein bestimmter NVT
    --force             vorhandene Bilder überschreiben
    --dpi 200           Auflösung der Renderings
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Aufruf per `python scripts/...`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf as fitz  # noqa: E402  (PyMuPDF; alias `fitz` beibehalten für Doku)

from app.config import get_settings  # noqa: E402

DEFAULT_PDF = Path(
    "/root/.claude/uploads/d9e3fd37-3923-50ea-9834-fe63e445f86e/"
    "ce660562-Roxel_alle_NVT_Einblasarbeiten_weiterer_Durchfu_hrungszeitraum_02072026.pdf"
)


def _render_page_as_png(doc: fitz.Document, page_index: int, out_path: Path, dpi: int) -> None:
    """1-indexed page_index → PNG. Rasterisiert die komplette Seite."""
    page = doc.load_page(page_index - 1)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_path)


def _extract_single_page_pdf(src: fitz.Document, page_index: int, out_path: Path) -> None:
    """1-indexed page_index → einseitige PDF."""
    out_doc = fitz.open()
    out_doc.insert_pdf(src, from_page=page_index - 1, to_page=page_index - 1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(out_path)
    out_doc.close()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def extract_reference_cases(
    pdf_path: Path,
    knowledge_root: Path,
    nvt_filter: str | None,
    force: bool,
    dpi: int,
) -> dict[str, int]:
    stats = {"nvt_written": 0, "nvt_skipped": 0, "nvt_no_page": 0}

    ref_root = knowledge_root / "referenzfaelle"
    if not ref_root.exists():
        return stats

    with fitz.open(pdf_path) as doc:
        n_pages = doc.page_count
        for entry_dir in sorted(ref_root.iterdir()):
            if not entry_dir.is_dir():
                continue
            metadata_path = entry_dir / "nvt.json"
            if not metadata_path.is_file():
                continue

            data = _load_json(metadata_path)
            nvt_number = str(data.get("nvt_number", ""))
            if nvt_filter and nvt_number != nvt_filter:
                continue

            source_page = data.get("source_page")
            if source_page is None:
                stats["nvt_no_page"] += 1
                continue
            if not (1 <= int(source_page) <= n_pages):
                print(f"  ! NVT {nvt_number}: source_page {source_page} außerhalb 1..{n_pages}")
                stats["nvt_no_page"] += 1
                continue

            photo_out = entry_dir / "photo.png"
            if photo_out.exists() and not force:
                stats["nvt_skipped"] += 1
            else:
                _render_page_as_png(doc, int(source_page), photo_out, dpi=dpi)
                stats["nvt_written"] += 1

            data["extracted_at"] = datetime.now(UTC).isoformat()
            _save_json(metadata_path, data)

    return stats


def extract_ruleplans(
    pdf_path: Path,
    knowledge_root: Path,
    force: bool,
    dpi: int,
) -> dict[str, int]:
    stats = {"plan_pdf_written": 0, "plan_pdf_skipped": 0, "preview_png_written": 0}

    rp_root = knowledge_root / "regelplaene"
    if not rp_root.exists():
        return stats

    with fitz.open(pdf_path) as doc:
        n_pages = doc.page_count
        for entry_dir in sorted(rp_root.iterdir()):
            if not entry_dir.is_dir():
                continue
            metadata_path = entry_dir / "metadata.json"
            if not metadata_path.is_file():
                continue

            data = _load_json(metadata_path)
            source_page = data.get("source_page")
            if source_page is None or not (1 <= int(source_page) <= n_pages):
                print(
                    f"  ! {entry_dir.name}: source_page fehlt oder außerhalb 1..{n_pages}"
                )
                continue

            plan_pdf = entry_dir / "plan.pdf"
            if plan_pdf.exists() and not force:
                stats["plan_pdf_skipped"] += 1
            else:
                _extract_single_page_pdf(doc, int(source_page), plan_pdf)
                stats["plan_pdf_written"] += 1

            preview_png = entry_dir / "preview.png"
            if force or not preview_png.exists():
                _render_page_as_png(doc, int(source_page), preview_png, dpi=dpi)
                stats["preview_png_written"] += 1

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Pfad zur Referenz-VRA-PDF")
    parser.add_argument("--nvt", type=str, default=None, help="Nur ein bestimmter NVT (z.B. 7107)")
    parser.add_argument("--force", action="store_true", help="Bestehende Bilder überschreiben")
    parser.add_argument("--dpi", type=int, default=180, help="Render-Auflösung (Default 180)")
    parser.add_argument(
        "--skip-ruleplans",
        action="store_true",
        help="Regelplan-Seiten nicht extrahieren",
    )
    parser.add_argument(
        "--skip-references",
        action="store_true",
        help="Referenzfall-Fotos nicht extrahieren",
    )
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"PDF nicht gefunden: {args.pdf}")
        print("Verwende --pdf um einen anderen Pfad anzugeben.")
        return 2

    settings = get_settings()
    knowledge_root = settings.knowledge_path

    print(f"→ Quelle: {args.pdf}")
    print(f"→ Ziel:   {knowledge_root}")
    print()

    if not args.skip_references:
        print("Referenzfälle:")
        rc_stats = extract_reference_cases(
            args.pdf, knowledge_root, args.nvt, args.force, args.dpi
        )
        print(
            f"  Fotos: {rc_stats['nvt_written']} geschrieben, "
            f"{rc_stats['nvt_skipped']} übersprungen, "
            f"{rc_stats['nvt_no_page']} ohne source_page"
        )
    print()

    if not args.skip_ruleplans:
        print("Regelpläne:")
        rp_stats = extract_ruleplans(args.pdf, knowledge_root, args.force, args.dpi)
        print(
            f"  plan.pdf:    {rp_stats['plan_pdf_written']} geschrieben, "
            f"{rp_stats['plan_pdf_skipped']} übersprungen"
        )
        print(f"  preview.png: {rp_stats['preview_png_written']} geschrieben")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
