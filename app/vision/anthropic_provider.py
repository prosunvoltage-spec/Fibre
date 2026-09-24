"""Anthropic-Claude-Vision-Provider (Default in Produktion).

Braucht ``ANTHROPIC_API_KEY`` in der Env. Wenn der Key fehlt, wird eine
Fehlerantwort zurückgegeben — die Pipeline eskaliert dann automatisch auf
``MANUELLE_PRUEFUNG``.

Wir nutzen strikt Multi-Image in einem Aufruf, damit das Modell Kontext
aggregieren kann (Master-Prompt §22, Build-Prompt §16).
"""

from __future__ import annotations

import base64
import json
import mimetypes
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings
from app.vision.base import ProviderResponse, VisionInput


@dataclass
class AnthropicVisionProvider:
    id: str = "anthropic"
    model: str | None = None
    max_output_tokens: int = 2048
    temperature: float = 0.0

    def __post_init__(self) -> None:
        settings = get_settings()
        self.model = self.model or settings.vision_model
        self._api_key = settings.anthropic_api_key or ""

    def analyze_photos(
        self,
        photos: list[VisionInput],
        prompt_text: str,
        prompt_hash: str,
        response_schema_hint: str,
    ) -> ProviderResponse:
        if not photos:
            return ProviderResponse(
                raw_text="",
                provider_id=self.id,
                model_id=self.model or "",
                errors=["no_photos"],
            )
        if not self._api_key:
            return ProviderResponse(
                raw_text="",
                provider_id=self.id,
                model_id=self.model or "",
                errors=["ANTHROPIC_API_KEY nicht gesetzt"],
            )

        try:
            import anthropic
        except ImportError:  # pragma: no cover
            return ProviderResponse(
                raw_text="",
                provider_id=self.id,
                model_id=self.model or "",
                errors=["anthropic-SDK nicht installiert"],
            )

        # Prompt-Nachrichteninhalt bauen
        content: list[dict] = [
            {"type": "text", "text": prompt_text},
            {
                "type": "text",
                "text": (
                    "\n\n# Erwartetes JSON-Schema (Antwort MUSS dazu passen)\n\n"
                    + response_schema_hint
                ),
            },
        ]
        for p in photos:
            img_bytes, media_type = _load_image_bytes(p.photo_path)
            if img_bytes is None:
                return ProviderResponse(
                    raw_text="",
                    provider_id=self.id,
                    model_id=self.model or "",
                    errors=[f"Foto nicht ladbar: {p.photo_path}"],
                )
            caption = f"photo_id={p.photo_id}"
            if p.caption:
                caption += f" ({p.caption})"
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.b64encode(img_bytes).decode("ascii"),
                    },
                }
            )
            content.append({"type": "text", "text": f"[Vorheriges Bild: {caption}]"})

        client = anthropic.Anthropic(api_key=self._api_key)
        start = time.perf_counter()
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                temperature=self.temperature,
                system=(
                    "Antworte ausschließlich mit gültigem JSON gemäß dem "
                    "angehängten Schema. Keine Prosa, keine Codeblöcke, "
                    "keine Regelplan-Empfehlungen."
                ),
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:
            return ProviderResponse(
                raw_text="",
                provider_id=self.id,
                model_id=self.model or "",
                errors=[f"anthropic_api_error: {type(exc).__name__}: {exc}"],
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        latency_ms = int((time.perf_counter() - start) * 1000)
        raw_text = ""
        refusal = False
        for block in getattr(resp, "content", []):
            block_type = getattr(block, "type", None)
            if block_type == "text":
                raw_text += getattr(block, "text", "")
            elif block_type == "refusal":
                refusal = True

        input_tokens = getattr(resp.usage, "input_tokens", 0) if hasattr(resp, "usage") else 0
        output_tokens = getattr(resp.usage, "output_tokens", 0) if hasattr(resp, "usage") else 0

        parsed = _try_parse_json(raw_text)
        errors: list[str] = []
        if refusal:
            errors.append("safety_refusal")
        elif parsed is None:
            errors.append("invalid_json")

        return ProviderResponse(
            raw_text=raw_text,
            parsed=parsed,
            provider_id=self.id,
            model_id=str(self.model),
            model_version=getattr(resp, "model", None),
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            latency_ms=latency_ms,
            errors=errors,
            refusal=refusal,
        )


def _load_image_bytes(path: Path) -> tuple[bytes | None, str]:
    if not path.is_file():
        return None, "application/octet-stream"
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/jpeg"
    return path.read_bytes(), mime


def _try_parse_json(raw: str) -> dict | None:
    text = raw.strip()
    if not text:
        return None
    # Modelle antworten manchmal mit ```json ... ``` — Codeblock strippen
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
        text = text.rstrip("`").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    return None
