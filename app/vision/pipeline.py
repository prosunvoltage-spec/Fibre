"""Vision-Pipeline: Provider-Aufruf mit Retry + Fallback auf MANUELLE_PRÜFUNG."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.vision.base import ProviderResponse, VisionInput, VisionProvider
from app.vision.prompts import LoadedPrompt
from app.vision.schema import VisionEnvironmentResponse, response_schema_json

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3


@dataclass
class VisionPipelineOutcome:
    """Ergebnis eines Pipeline-Laufs für einen NVT."""

    response: VisionEnvironmentResponse | None
    raw_provider_response: ProviderResponse | None
    attempts: int
    manual_review_required: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        return self.response is not None


class VisionPipeline:
    """Kapselt Prompt-Verwendung, Retry-Kette und Schema-Validierung."""

    def __init__(self, provider: VisionProvider, prompt: LoadedPrompt) -> None:
        self.provider = provider
        self.prompt = prompt

    def analyze(self, photos: list[VisionInput]) -> VisionPipelineOutcome:
        if not photos:
            return VisionPipelineOutcome(
                response=None,
                raw_provider_response=None,
                attempts=0,
                manual_review_required=True,
                errors=["Keine Fotos übergeben"],
            )

        errors: list[str] = []
        last_raw: ProviderResponse | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            prompt_text = self.prompt.text
            if attempt > 1:
                prompt_text += (
                    "\n\n# Wiederholung\n"
                    "Deine vorherige Antwort war ungültig. "
                    "Antworte NUR mit reinem JSON, ohne Prosa, ohne Codeblock."
                )

            raw = self.provider.analyze_photos(
                photos=photos,
                prompt_text=prompt_text,
                prompt_hash=self.prompt.sha256,
                response_schema_hint=response_schema_json(),
            )
            last_raw = raw

            if raw.refusal:
                return VisionPipelineOutcome(
                    response=None,
                    raw_provider_response=raw,
                    attempts=attempt,
                    manual_review_required=True,
                    errors=["safety_refusal"],
                )

            if raw.errors and raw.parsed is None:
                errors.extend(raw.errors)
                continue

            if raw.parsed is None:
                errors.append("provider_returned_empty")
                continue

            try:
                response = VisionEnvironmentResponse(**raw.parsed)
            except ValidationError as exc:
                errors.append(f"schema_validation_failed:{exc.error_count()}")
                logger.warning("Vision-Schema-Fehler (Versuch %d): %s", attempt, exc)
                continue

            warnings = _postvalidate(response)
            manual = response.manual_review_suggested or bool(warnings)
            return VisionPipelineOutcome(
                response=response,
                raw_provider_response=raw,
                attempts=attempt,
                manual_review_required=manual,
                warnings=warnings,
            )

        return VisionPipelineOutcome(
            response=None,
            raw_provider_response=last_raw,
            attempts=_MAX_ATTEMPTS,
            manual_review_required=True,
            errors=errors or ["unknown_provider_error"],
        )


_FORBIDDEN_CLAIMS = (
    "rsa 21 schreibt",
    "rsa21 schreibt",
    "nach stvo",
    "vwv-stvo",
    "empfohlener regelplan",
    "empfohlener plan",
    "wir empfehlen",
    "regelplan-vorschlag",
)


def _postvalidate(response: VisionEnvironmentResponse) -> list[str]:
    """Halluzinations-Schutz auf der Response.

    Prüft Freitextfelder auf verbotene Rechtsquellen-Zitate oder
    Regelplan-Empfehlungen. Fund → Warnung + Feldbereinigung.
    """
    warnings: list[str] = []

    def _scrub(items: list[str], location: str) -> list[str]:
        clean = []
        for it in items:
            lower = it.lower()
            if any(f in lower for f in _FORBIDDEN_CLAIMS):
                warnings.append(f"Halluzinations-Verdacht in {location}: '{it[:60]}' verworfen")
                continue
            clean.append(it)
        return clean

    response.existing_signs = _scrub(response.existing_signs, "existing_signs")
    response.existing_barriers = _scrub(response.existing_barriers, "existing_barriers")
    response.obstacles = _scrub(response.obstacles, "obstacles")
    response.uncertainties = _scrub(response.uncertainties, "uncertainties")
    return warnings
