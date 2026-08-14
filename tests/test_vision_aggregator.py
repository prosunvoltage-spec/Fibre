"""Tests für Multi-Foto-Aggregation."""

from __future__ import annotations

from decimal import Decimal

from app.core.enums import NvtPosition, RoadClass, Ternary
from app.vision.aggregator import aggregate_multi_photo
from app.vision.schema import VisionEnvironmentResponse


def test_single_photo_passes_through() -> None:
    r = VisionEnvironmentResponse(road_present=Ternary.YES, vision_confidence=Decimal("0.8"))
    out = aggregate_multi_photo([r])
    assert out is r


def test_yes_no_yields_unknown_and_contradiction() -> None:
    a = VisionEnvironmentResponse(cycleway_present=Ternary.YES)
    b = VisionEnvironmentResponse(cycleway_present=Ternary.NO)
    out = aggregate_multi_photo([a, b])
    assert out.cycleway_present == Ternary.UNKNOWN
    assert any("cycleway_present" in c for c in out.contradictions)
    assert out.manual_review_suggested is True


def test_yes_unknown_stays_yes() -> None:
    a = VisionEnvironmentResponse(sidewalk_present=Ternary.YES)
    b = VisionEnvironmentResponse(sidewalk_present=Ternary.UNKNOWN)
    out = aggregate_multi_photo([a, b])
    assert out.sidewalk_present == Ternary.YES


def test_position_conflict_falls_back_to_unknown() -> None:
    a = VisionEnvironmentResponse(nvt_position=NvtPosition.AT_ROADSIDE)
    b = VisionEnvironmentResponse(nvt_position=NvtPosition.BEHIND_SIDEWALK)
    out = aggregate_multi_photo([a, b])
    assert out.nvt_position == NvtPosition.UNKNOWN
    assert any("nvt_position" in c for c in out.contradictions)


def test_confidence_is_minimum() -> None:
    a = VisionEnvironmentResponse(vision_confidence=Decimal("0.9"))
    b = VisionEnvironmentResponse(vision_confidence=Decimal("0.5"))
    out = aggregate_multi_photo([a, b])
    assert out.vision_confidence == Decimal("0.5")


def test_number_averaging_within_tolerance() -> None:
    a = VisionEnvironmentResponse(sidewalk_width_m=Decimal("1.5"))
    b = VisionEnvironmentResponse(sidewalk_width_m=Decimal("1.6"))
    out = aggregate_multi_photo([a, b])
    assert out.sidewalk_width_m is not None
    assert Decimal("1.5") <= out.sidewalk_width_m <= Decimal("1.6")


def test_number_too_divergent_is_dropped() -> None:
    a = VisionEnvironmentResponse(roadway_width_m=Decimal("3.0"))
    b = VisionEnvironmentResponse(roadway_width_m=Decimal("6.0"))
    out = aggregate_multi_photo([a, b])
    assert out.roadway_width_m is None


def test_lists_merged_and_deduplicated() -> None:
    a = VisionEnvironmentResponse(existing_signs=["Z 274-30", "Z 283"])
    b = VisionEnvironmentResponse(existing_signs=["Z 274-30", "Z 259"])
    out = aggregate_multi_photo([a, b])
    assert out.existing_signs == ["Z 274-30", "Z 283", "Z 259"]
