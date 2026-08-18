"""Tests für Vision-Pipeline: Retry-Kette, Fallback, Halluzinations-Schutz."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.enums import NvtPosition, RoadClass, Ternary
from app.vision import MockVisionProvider, VisionInput, VisionPipeline
from app.vision.prompts import LoadedPrompt


@pytest.fixture()
def dummy_prompt() -> LoadedPrompt:
    return LoadedPrompt(
        name="test",
        version=1,
        text="Analysiere die Fotos.",
        frontmatter={"version": 1},
        sha256="a" * 64,
        path=Path("/tmp/test.md"),
    )


def _photo(name: str) -> VisionInput:
    return VisionInput(photo_path=Path(f"/tmp/{name}"), photo_id=name)


def test_success_first_attempt(dummy_prompt: LoadedPrompt) -> None:
    provider = MockVisionProvider(
        responses={
            "a.jpg": {
                "road_present": "yes",
                "sidewalk_present": "yes",
                "cycleway_present": "no",
                "nvt_position": "at_roadside",
                "road_class": "wohnstrasse",
                "vision_confidence": 0.9,
                "manual_review_suggested": False,
            }
        }
    )
    pipeline = VisionPipeline(provider, dummy_prompt)
    outcome = pipeline.analyze([_photo("a.jpg")])
    assert outcome.is_ok()
    assert outcome.attempts == 1
    assert outcome.response is not None
    assert outcome.response.road_present == Ternary.YES
    assert not outcome.manual_review_required


def test_empty_photos_returns_manual_review(dummy_prompt: LoadedPrompt) -> None:
    pipeline = VisionPipeline(MockVisionProvider(), dummy_prompt)
    outcome = pipeline.analyze([])
    assert not outcome.is_ok()
    assert outcome.manual_review_required


def test_safety_refusal_escalates(dummy_prompt: LoadedPrompt) -> None:
    provider = MockVisionProvider(force_refusal=True)
    pipeline = VisionPipeline(provider, dummy_prompt)
    outcome = pipeline.analyze([_photo("a.jpg")])
    assert not outcome.is_ok()
    assert outcome.manual_review_required
    assert "safety_refusal" in outcome.errors


def test_invalid_json_retried_then_manual_review(dummy_prompt: LoadedPrompt) -> None:
    provider = MockVisionProvider(force_invalid_json=True)
    pipeline = VisionPipeline(provider, dummy_prompt)
    outcome = pipeline.analyze([_photo("a.jpg")])
    assert not outcome.is_ok()
    assert outcome.attempts == 3
    assert outcome.manual_review_required


def test_default_unknown_response_flags_manual_review(dummy_prompt: LoadedPrompt) -> None:
    """Ohne hinterlegten Response → alles UNKNOWN → manual_review_suggested=True."""
    pipeline = VisionPipeline(MockVisionProvider(), dummy_prompt)
    outcome = pipeline.analyze([_photo("unbekannt.jpg")])
    assert outcome.is_ok()
    assert outcome.response is not None
    assert outcome.response.count_unknowns() == outcome.response.total_countable_fields()
    assert outcome.manual_review_required


def test_forbidden_freetext_stripped(dummy_prompt: LoadedPrompt) -> None:
    provider = MockVisionProvider(
        responses={
            "a.jpg": {
                "road_present": "yes",
                "obstacles": ["Baum", "Wir empfehlen Regelplan B1/2"],
                "uncertainties": ["RSA 21 schreibt hier folgendes vor: …"],
                "vision_confidence": 0.8,
            }
        }
    )
    pipeline = VisionPipeline(provider, dummy_prompt)
    outcome = pipeline.analyze([_photo("a.jpg")])
    assert outcome.is_ok()
    assert outcome.response is not None
    # RSA-Zitat und Regelplan-Vorschlag sind verworfen
    assert "Baum" in outcome.response.obstacles
    assert not any("empfehlen regelplan" in o.lower() for o in outcome.response.obstacles)
    assert all("rsa 21 schreibt" not in u.lower() for u in outcome.response.uncertainties)
    assert outcome.warnings  # Halluzinations-Warnung wurde geloggt
