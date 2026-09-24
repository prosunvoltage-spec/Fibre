"""Tesseract-basierter OCR-Provider (offline, Default)."""

from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image

from app.config import get_settings
from app.ocr.base import OCRResult


class TesseractOCRProvider:
    id = "tesseract"

    def __init__(self, languages: str = "deu+eng") -> None:
        self.languages = languages
        settings = get_settings()
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def ocr_photo(self, photo_path: Path) -> OCRResult:
        warnings: list[str] = []
        if not photo_path.is_file():
            return OCRResult(
                text="",
                provider=self.id,
                language=self.languages,
                warnings=[f"Datei nicht gefunden: {photo_path}"],
            )

        try:
            with Image.open(photo_path) as img:
                img.load()
                text = pytesseract.image_to_string(img, lang=self.languages)
                data = pytesseract.image_to_data(
                    img, lang=self.languages, output_type=pytesseract.Output.DICT
                )
        except pytesseract.TesseractNotFoundError:
            return OCRResult(
                text="",
                provider=self.id,
                language=self.languages,
                warnings=["Tesseract-Binary nicht gefunden (TESSERACT_CMD prüfen)"],
            )
        except Exception as exc:  # pragma: no cover — Tesseract-Randfälle
            return OCRResult(
                text="",
                provider=self.id,
                language=self.languages,
                warnings=[f"Tesseract-Fehler: {exc}"],
            )

        words: list[dict[str, object]] = []
        confidences: list[float] = []
        for i in range(len(data.get("text", []))):
            word = (data["text"][i] or "").strip()
            if not word:
                continue
            try:
                conf_raw = float(data["conf"][i])
            except (TypeError, ValueError):
                conf_raw = -1.0
            if conf_raw < 0:
                continue
            confidences.append(conf_raw)
            words.append(
                {
                    "text": word,
                    "conf": conf_raw / 100.0,
                    "x": int(data["left"][i]),
                    "y": int(data["top"][i]),
                    "w": int(data["width"][i]),
                    "h": int(data["height"][i]),
                }
            )

        confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

        if not text.strip():
            warnings.append("OCR lieferte keinen Text")

        return OCRResult(
            text=text,
            confidence=confidence,
            language=self.languages,
            provider=self.id,
            words=words,
            warnings=warnings,
        )
