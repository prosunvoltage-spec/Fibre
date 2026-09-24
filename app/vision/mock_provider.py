"""Mock-Vision-Provider für Tests und Betrieb ohne API-Key.

Verhält sich deterministisch: gibt entweder eine hinterlegte Antwort
zurück, oder eine leere Antwort mit ``manual_review_suggested=True``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.vision.base import ProviderResponse, VisionInput


@dataclass
class MockVisionProvider:
    """Deterministischer Fake für Tests.

    Antworten können pro (Set-of-photo-basenames, sortiert) hinterlegt werden.
    Fehlt ein Eintrag, liefert der Provider ein „unknown"-Fallback-Ergebnis.
    """

    id: str = "mock"
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    default_confidence: float = 0.5
    force_errors: list[str] = field(default_factory=list)
    force_refusal: bool = False
    force_invalid_json: bool = False

    def analyze_photos(
        self,
        photos: list[VisionInput],
        prompt_text: str,
        prompt_hash: str,
        response_schema_hint: str,
    ) -> ProviderResponse:
        start = time.perf_counter()

        if self.force_refusal:
            return ProviderResponse(
                raw_text="",
                provider_id=self.id,
                model_id="mock",
                errors=["safety_refusal"],
                refusal=True,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        if self.force_invalid_json:
            return ProviderResponse(
                raw_text="das ist kein JSON",
                provider_id=self.id,
                model_id="mock",
                errors=["invalid_json"],
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        if self.force_errors:
            return ProviderResponse(
                raw_text="",
                provider_id=self.id,
                model_id="mock",
                errors=list(self.force_errors),
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        key = self._key(photos)
        payload = self.responses.get(key)
        if payload is None:
            payload = _default_unknown_payload(self.default_confidence)

        raw = json.dumps(payload, ensure_ascii=False)
        return ProviderResponse(
            raw_text=raw,
            parsed=payload,
            provider_id=self.id,
            model_id="mock-1",
            model_version="1.0",
            input_tokens=len(prompt_text.split()),
            output_tokens=len(raw.split()),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    @staticmethod
    def _key(photos: list[VisionInput]) -> str:
        return ",".join(sorted(p.photo_path.name for p in photos))


def _default_unknown_payload(confidence: float) -> dict[str, Any]:
    """Konservatives Fallback: alles UNKNOWN + manual_review_suggested=True."""
    return {
        "road_present": "unknown",
        "sidewalk_present": "unknown",
        "cycleway_present": "unknown",
        "shared_cycle_footway_present": "unknown",
        "parking_lane_present": "unknown",
        "seiten_streifen_present": "unknown",
        "private_property": "unknown",
        "business_property": "unknown",
        "driveway_present": "unknown",
        "intersection_present": "unknown",
        "junction_present": "unknown",
        "cul_de_sac": "unknown",
        "curve_present": "unknown",
        "bus_stop_nearby": "unknown",
        "fire_access": "unknown",
        "nvt_position": "unknown",
        "road_class": "unknown",
        "parked_vehicles_in_workarea": "unknown",
        "existing_signs": [],
        "existing_barriers": [],
        "obstacles": [],
        "sight_relations_affected": "unknown",
        "vision_confidence": confidence,
        "uncertainties": ["Kein hinterlegter Mock-Response für diese Fotos"],
        "contradictions": [],
        "manual_review_suggested": True,
        "per_photo_notes": {},
    }
