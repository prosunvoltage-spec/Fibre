"""Tests für VisionEnvironmentResponse."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.enums import NvtPosition, RoadClass, Ternary
from app.vision.schema import VisionEnvironmentResponse, response_schema_json


def test_defaults_are_unknown() -> None:
    r = VisionEnvironmentResponse()
    assert r.road_present == Ternary.UNKNOWN
    assert r.nvt_position == NvtPosition.UNKNOWN
    assert r.road_class == RoadClass.UNKNOWN
    assert r.vision_confidence == Decimal("0")
    assert r.data_completeness() == Decimal("0")


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        VisionEnvironmentResponse(recommended_ruleplan="B1/2")  # type: ignore[call-arg]


def test_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        VisionEnvironmentResponse(vision_confidence=Decimal("1.5"))


def test_ruleplan_reference_in_freetext_scrubbed() -> None:
    r = VisionEnvironmentResponse(
        obstacles=[
            "Hydrant",
            "Vorschlag: B1/2",  # muss vom Validator entfernt werden
        ]
    )
    assert "Hydrant" in r.obstacles
    assert all("b1/2" not in o.lower() for o in r.obstacles)


def test_data_completeness_calculation() -> None:
    r = VisionEnvironmentResponse(
        road_present=Ternary.YES,
        sidewalk_present=Ternary.YES,
        cycleway_present=Ternary.NO,
        nvt_position=NvtPosition.AT_ROADSIDE,
        road_class=RoadClass.HAUPTVERKEHR,
    )
    # 19 zählbare Felder, davon 5 gesetzt → 14 unknown, 5/19 completeness
    assert 0 < r.data_completeness() < 1
    assert r.count_unknowns() == 14


def test_all_ternary_yes_gives_full_completeness() -> None:
    values = {
        f: Ternary.YES
        for f in (
            "road_present", "sidewalk_present", "cycleway_present",
            "shared_cycle_footway_present", "parking_lane_present",
            "seiten_streifen_present", "private_property", "business_property",
            "driveway_present", "intersection_present", "junction_present",
            "cul_de_sac", "curve_present", "bus_stop_nearby", "fire_access",
            "parked_vehicles_in_workarea", "sight_relations_affected",
        )
    }
    r = VisionEnvironmentResponse(
        **values,
        nvt_position=NvtPosition.AT_ROADSIDE,
        road_class=RoadClass.WOHNSTRASSE,
    )
    assert r.data_completeness() == Decimal("1")


def test_schema_json_is_valid() -> None:
    import json

    schema = json.loads(response_schema_json())
    assert schema["type"] == "object"
    assert "road_present" in schema["properties"]
    assert schema.get("additionalProperties") is False
