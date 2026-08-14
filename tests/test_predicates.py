"""Tests für Rule-Engine-Prädikate."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.enums import NvtPosition, RoadClass, Ternary
from app.core.schemas import EnvironmentAnalysisSchema, WorkAreaSchema
from app.rules import predicates as p
from app.rules.predicates import (
    PREDICATE_REGISTRY,
    UnknownPredicate,
    evaluate_predicate,
)


def _env(**overrides) -> EnvironmentAnalysisSchema:  # type: ignore[no-untyped-def]
    return EnvironmentAnalysisSchema(nvt_id=uuid4(), **overrides)


def _wa(**overrides) -> WorkAreaSchema:  # type: ignore[no-untyped-def]
    return WorkAreaSchema(nvt_id=uuid4(), **overrides)


# ---- Verkehrsraum -------------------------------------------------------

def test_has_sidewalk_yes() -> None:
    assert p.has_sidewalk(_env(sidewalk_present=Ternary.YES)) == Ternary.YES


def test_has_sidewalk_unknown() -> None:
    assert p.has_sidewalk(_env()) == Ternary.UNKNOWN


def test_is_cul_de_sac_from_road_class() -> None:
    e = _env(road_class=RoadClass.SACKGASSE)
    assert p.is_cul_de_sac(e) == Ternary.YES


def test_is_intersection_area_or_junction() -> None:
    assert p.is_intersection_area(_env(intersection_present=Ternary.YES)) == Ternary.YES
    assert p.is_intersection_area(_env(junction_present=Ternary.YES)) == Ternary.YES
    assert p.is_intersection_area(_env(intersection_present=Ternary.NO, junction_present=Ternary.NO)) == Ternary.NO


def test_is_main_road_from_class() -> None:
    assert p.is_main_road(_env(road_class=RoadClass.HAUPTVERKEHR)) == Ternary.YES
    assert p.is_main_road(_env(road_class=RoadClass.WOHNSTRASSE)) == Ternary.NO
    assert p.is_main_road(_env()) == Ternary.UNKNOWN


def test_is_operating_area_from_business_property() -> None:
    assert p.is_operating_area(_env(business_property=Ternary.YES)) == Ternary.YES
    assert p.is_operating_area(_env(nvt_position=NvtPosition.ON_BUSINESS_PREMISES)) == Ternary.YES


# ---- WorkArea-Prädikate -------------------------------------------------

def test_road_affected_from_workarea() -> None:
    e = _env(road_present=Ternary.YES)
    wa = _wa(affects_road=True)
    assert p.road_affected(e, wa) == Ternary.YES


def test_road_affected_from_position() -> None:
    e = _env(road_present=Ternary.YES, nvt_position=NvtPosition.AT_ROADSIDE)
    assert p.road_affected(e, None) == Ternary.YES


def test_road_affected_no_when_no_road() -> None:
    assert p.road_affected(_env(road_present=Ternary.NO), None) == Ternary.NO


def test_sidewalk_affected_unknown_without_wa() -> None:
    e = _env(sidewalk_present=Ternary.YES)  # position unbekannt
    assert p.sidewalk_affected(e, None) == Ternary.UNKNOWN


# ---- Zahlen -------------------------------------------------------------

def test_remaining_roadway_ge_from_workarea() -> None:
    wa = _wa(remaining_roadway_width_m=Decimal("3.5"))
    assert p.remaining_roadway_ge(_env(), wa, 3.0) == Ternary.YES
    assert p.remaining_roadway_ge(_env(), wa, 4.0) == Ternary.NO


def test_remaining_roadway_ge_unknown_without_data() -> None:
    assert p.remaining_roadway_ge(_env(), None, 3.0) == Ternary.UNKNOWN


# ---- Registry -----------------------------------------------------------

def test_registry_covers_common_predicates() -> None:
    expected = {
        "has_road", "has_sidewalk", "has_cycleway", "is_cul_de_sac",
        "is_intersection_area", "is_private_property", "is_business_property",
        "is_residential_street", "is_main_road", "road_affected",
        "sidewalk_affected", "cycleway_affected", "remaining_roadway_ge",
    }
    assert expected.issubset(PREDICATE_REGISTRY.keys())


def test_evaluate_predicate_delegates() -> None:
    assert evaluate_predicate("has_sidewalk", _env(sidewalk_present=Ternary.YES)) == Ternary.YES


def test_evaluate_predicate_with_args() -> None:
    wa = _wa(remaining_roadway_width_m=Decimal("3.5"))
    assert evaluate_predicate("remaining_roadway_ge", _env(), wa=wa, args={"min_m": 3.0}) == Ternary.YES


def test_unknown_predicate_raises() -> None:
    with pytest.raises(UnknownPredicate):
        evaluate_predicate("does_not_exist", _env())
