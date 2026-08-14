"""Tesseract-basierter OCR-Provider (Default, offline).

Nutzt ``pytesseract.image_to_data`` — liefert Wörter mit Position und
Konfidenz, statt nur einem Freitext. Damit können wir spätere Parser
(NVT-Nummer aus Typenschild vs. Adresse aus Overlay) räumlich trennen.
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

import pytesseract
from PIL import Image
from pytesseract import Output

from app.config import get_settings
from app.ocr.base import OcrResult, TextBlock


class TesseractOCRProvider:
    """Offline-OCR über eine lokale Tesseract-Installation.

    Voraussetzung: Systempaket ``tesseract-ocr`` plus Sprachdaten
    (``tesseract-ocr-deu`` für Deutsch). Der Pfad zum Binary lässt sich
    per ``TESSERACT_CMD`` überschreiben.
    """

    id = "tesseract"

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        cmd = tesseract_cmd or get_settings().tesseract_cmd
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        try:
            self.version = str(pytesseract.get_tesseract_version())
        except (pytesseract.TesseractNotFoundError, OSError) as exc:
            raise RuntimeError(
                "Tesseract nicht gefunden. Bitte 'tesseract-ocr' installieren "
                "oder TESSERACT_CMD auf das Binary setzen."
            ) from exc

    def ocr_photo(self, image_bytes: bytes, *, language: str = "deu+eng") -> OcrResult:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        width, height = image.size
        data: dict[str, Any] = pytesseract.image_to_data(
            image, lang=language, output_type=Output.DICT
        )

        blocks: list[TextBlock] = []
        pieces: list[str] = []
        for i, text in enumerate(data.get("text", [])):
            text = (text or "").strip()
            if not text:
                continue
            raw_conf = data["conf"][i]
            try:
                conf_val = float(raw_conf)
            except (TypeError, ValueError):
                continue
            if conf_val < 0:
                continue

            left = float(data["left"][i])
            top = float(data["top"][i])
            w = float(data["width"][i])
            h = float(data["height"][i])
            line_num = int(data.get("line_num", [0] * (i + 1))[i])

            blocks.append(
                TextBlock(
                    text=text,
                    bbox_x=Decimal(str(round(left / width, 6))),
                    bbox_y=Decimal(str(round(top / height, 6))),
                    bbox_w=Decimal(str(round(w / width, 6))),
                    bbox_h=Decimal(str(round(h / height, 6))),
                    confidence=Decimal(str(round(min(max(conf_val, 0.0), 100.0) / 100, 6))),
                    line=line_num,
                )
            )
            pieces.append(text)

        return OcrResult(
            text=" ".join(pieces),
            blocks=blocks,
            language=language,
            provider=self.id,
            provider_version=self.version,
            image_width=width,
            image_height=height,
            raw={},
        )
