"""Tests für Pydantic-Schemas — Validierung, extra=forbid, Wertegrenzen."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.enums import (
    AddressSource,
    DecisionCode,
    NvtPosition,
    OverlaySymbolType,
    ReviewAction,
    Ternary,
    TrafficUser,
)
from app.core.schemas import (
    AddressSchema,
    DecisionSchema,
    EnvironmentAnalysisSchema,
    LocationSchema,
    NvtCreate,
    OverlayPointSchema,
    OverlayShapeSchema,
    OverlaySymbolSchema,
    ProjectCreate,
    ReviewCreate,
    TrafficUserAssessmentSchema,
    WorkAreaSchema,
)


# ---- Address -------------------------------------------------------------

def test_address_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        AddressSchema(street="Musterstraße", unknown_field=1)  # type: ignore[call-arg]


def test_address_source_enum() -> None:
    addr = AddressSchema(street="X", source=AddressSource.OCR)
    assert addr.source == AddressSource.OCR


# ---- Location ------------------------------------------------------------

def test_location_lat_out_of_range() -> None:
    with pytest.raises(ValidationError):
        LocationSchema(latitude=Decimal("120"))


def test_location_lon_out_of_range() -> None:
    with pytest.raises(ValidationError):
        LocationSchema(longitude=Decimal("-200"))


def test_location_valid() -> None:
    loc = LocationSchema(latitude=Decimal("51.9"), longitude=Decimal("7.5"))
    assert loc.latitude == Decimal("51.9")


# ---- Project -------------------------------------------------------------

def test_project_create_requires_contractor() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(
            name="Roxel",
            ruleset_version="v1",
            vision_provider="anthropic",
        )  # type: ignore[call-arg]


def test_project_create_ok() -> None:
    p = ProjectCreate(
        name="Roxel",
        contractor="Helder Santos",
        ruleset_version="v1",
        vision_provider="anthropic",
    )
    assert p.name == "Roxel"


# ---- NVT -----------------------------------------------------------------

def test_nvt_create_ok() -> None:
    nvt = NvtCreate(
        project_id=uuid4(),
        nvt_number="7107",
        address=AddressSchema(street="Roxeler Straße", house_number="579"),
    )
    assert nvt.nvt_number == "7107"


def test_nvt_create_empty_number_rejected() -> None:
    with pytest.raises(ValidationError):
        NvtCreate(project_id=uuid4(), nvt_number="")


# ---- EnvironmentAnalysis -------------------------------------------------

def test_environment_defaults_are_unknown() -> None:
    env = EnvironmentAnalysisSchema(nvt_id=uuid4())
    assert env.road_present == Ternary.UNKNOWN
    assert env.sidewalk_present == Ternary.UNKNOWN
    assert env.nvt_position == NvtPosition.UNKNOWN
    assert env.data_completeness == Decimal("0")


def test_environment_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        EnvironmentAnalysisSchema(nvt_id=uuid4(), vision_confidence=Decimal("1.5"))


def test_environment_completeness_negative() -> None:
    with pytest.raises(ValidationError):
        EnvironmentAnalysisSchema(nvt_id=uuid4(), data_completeness=Decimal("-0.1"))


def test_environment_forbids_extra_field() -> None:
    """Halluzinations-Schutz: recommended_ruleplan darf nicht durchkommen."""
    with pytest.raises(ValidationError):
        EnvironmentAnalysisSchema(
            nvt_id=uuid4(),
            recommended_ruleplan="B1/2",  # type: ignore[call-arg]
        )


# ---- Overlay -------------------------------------------------------------

def test_overlay_point_in_unit_interval() -> None:
    OverlayPointSchema(x=Decimal("0.5"), y=Decimal("0.5"))
    with pytest.raises(ValidationError):
        OverlayPointSchema(x=Decimal("1.5"), y=Decimal("0.5"))


def test_overlay_shape_needs_two_points() -> None:
    with pytest.raises(ValidationError):
        OverlayShapeSchema(
            kind="polygon",
            points=[OverlayPointSchema(x=Decimal("0.1"), y=Decimal("0.1"))],
        )


def test_overlay_symbol_type_enum() -> None:
    sym = OverlaySymbolSchema(
        type=OverlaySymbolType.LEITBAKE,
        x=Decimal("0.5"),
        y=Decimal("0.5"),
    )
    assert sym.type == OverlaySymbolType.LEITBAKE


# ---- WorkArea ------------------------------------------------------------

def test_workarea_defaults() -> None:
    wa = WorkAreaSchema(nvt_id=uuid4())
    assert wa.bulli_length_m == Decimal("5.5")
    assert wa.affects_road is False


# ---- TrafficUser --------------------------------------------------------

def test_traffic_user_assessment() -> None:
    tua = TrafficUserAssessmentSchema(
        nvt_id=uuid4(),
        user=TrafficUser.PEDESTRIAN,
        affected=True,
        proposed_route="Über gegenüberliegenden Gehweg",
        safe=Ternary.YES,
    )
    assert tua.user == TrafficUser.PEDESTRIAN


# ---- Decision -----------------------------------------------------------

def test_decision_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        DecisionSchema(
            nvt_id=uuid4(),
            code=DecisionCode.AUTO_VORSCHLAG,
            rule_confidence=Decimal("2"),
            ruleset_version="v1",
        )


def test_decision_privatflaeche_without_ruleplan_is_ok() -> None:
    d = DecisionSchema(
        nvt_id=uuid4(),
        code=DecisionCode.PRIVATFLAECHE,
        ruleset_version="v1",
        selected_ruleplan_id=None,
    )
    assert d.code == DecisionCode.PRIVATFLAECHE
    assert d.selected_ruleplan_id is None


# ---- Review --------------------------------------------------------------

def test_review_requires_reviewer_and_action() -> None:
    with pytest.raises(ValidationError):
        ReviewCreate(nvt_id=uuid4(), reviewer="", action=ReviewAction.APPROVED)


def test_review_ok() -> None:
    r = ReviewCreate(
        nvt_id=uuid4(),
        reviewer="nico.n",
        action=ReviewAction.RULEPLAN_CHANGED,
        comment="Verkehrsstärke höher als angenommen",
        before={"ruleplan": "B1/2"},
        after={"ruleplan": "B2/2"},
    )
    assert r.action == ReviewAction.RULEPLAN_CHANGED
