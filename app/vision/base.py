"""Provider-Interface + Datenobjekte für Vision-Adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class VisionInput:
    """Ein Foto plus Kontext für die Vision-Anfrage."""

    photo_path: Path
    photo_id: str
    caption: str | None = None  # z.B. "Front", "Straßenseite"


@dataclass
class ProviderResponse:
    """Rohantwort eines Vision-Providers vor Schema-Validierung."""

    raw_text: str                              # Rohantwort des Modells
    parsed: dict | None = None                 # geparstes JSON (None bei Fehler)
    provider_id: str = ""
    model_id: str = ""
    model_version: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    errors: list[str] = field(default_factory=list)
    refusal: bool = False                      # Safety-Refusal

    def is_ok(self) -> bool:
        return self.parsed is not None and not self.errors and not self.refusal


class VisionProvider(Protocol):
    """Vertrag für alle Vision-Adapter (Claude, OpenAI, lokal, …)."""

    id: str

    def analyze_photos(
        self,
        photos: list[VisionInput],
        prompt_text: str,
        prompt_hash: str,
        response_schema_hint: str,
    ) -> ProviderResponse:
        """Sendet ein oder mehrere Fotos + Prompt und erwartet strikt JSON.

        - ``photos`` — Alle Fotos eines NVT in einem Aufruf (Kontext).
        - ``prompt_text`` — bereits geladener Prompt (aus prompts/*.md).
        - ``prompt_hash`` — SHA-256 des Prompts (für Audit).
        - ``response_schema_hint`` — JSON-Schema des erwarteten Outputs
          als Prompt-Anhang, für strengere Provider-Steuerung.

        Antwort: :class:`ProviderResponse`. Fehler landen in ``errors``, das
        Rückgabeobjekt wird immer geliefert.
        """
        ...
