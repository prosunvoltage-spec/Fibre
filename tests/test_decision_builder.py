"""Tests für DecisionBuilder (DB-Persistierung + Statuswechsel)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.classification.decision_builder import DecisionBuilder
from app.core.enums import DecisionCode, NvtStatus, PhotoKind, Ternary
from app.core.models import EnvironmentAnalysis, Nvt, Photo, Project
from app.core.repositories import ProjectRepo
from app.core.schemas import ProjectCreate
from app.ruleplans import RulePlanLibrary


@pytest.fixture()
def library(tmp_path: Path) -> RulePlanLibrary:
    root = tmp_path / "rp"
    p = root / "PLAN_A"
    p.mkdir(parents=True)
    (p / "plan.pdf").write_bytes(b"%PDF")
    (p / "preview.png").write_bytes(b"\x89PNG")
    (p / "metadata.json").write_text(
        json.dumps(
            {
                "id": "PLAN_A",
                "name": "Plan A",
                "quelle": "T",
                "verkehrsraum": ["innerorts"],
                "geeignet_fuer": [{"predicate": "has_sidewalk", "value": "yes"}],
                "voraussetzungen": [],
                "ausschlusskriterien": [],
                "allowed_symbols": ["leitbake"],
            }
        )
    )
    return RulePlanLibrary(root).load()


def _make_nvt_with_env(
    session: Session, nvt_status: NvtStatus = NvtStatus.ANALYZED,
) -> Nvt:
    project = ProjectRepo(session).create(
        ProjectCreate(name="P", contractor="F", ruleset_version="v1", vision_provider="mock")
    )
    nvt = Nvt(project_id=project.id, nvt_number="7107", warnings_json=[], status=nvt_status)
    session.add(nvt)
    session.flush()
    env = EnvironmentAnalysis(
        nvt_id=nvt.id,
        road_present=Ternary.YES,
        sidewalk_present=Ternary.YES,
        cycleway_present=Ternary.NO,
        shared_cycle_footway_present=Ternary.NO,
        parking_lane_present=Ternary.NO,
        seiten_streifen_present=Ternary.NO,
        private_property=Ternary.NO,
        business_property=Ternary.NO,
        driveway_present=Ternary.NO,
        intersection_present=Ternary.NO,
        junction_present=Ternary.NO,
        cul_de_sac=Ternary.NO,
        curve_present=Ternary.NO,
        bus_stop_nearby=Ternary.NO,
        fire_access=Ternary.NO,
        parked_vehicles_in_workarea=Ternary.NO,
        sight_relations_affected=Ternary.NO,
        vision_confidence=Decimal("0.9"),
        data_completeness=Decimal("1"),
        model_id="mock",
        prompt_hash="abc",
        created_at=datetime.now(UTC),
    )
    nvt.environment = env
    session.add(env)
    session.flush()
    return nvt


def test_decide_creates_decision_and_candidates(session: Session, library: RulePlanLibrary) -> None:
    nvt = _make_nvt_with_env(session)
    builder = DecisionBuilder(session, library=library, ruleset_version="v1")
    outcome = builder.decide_for_nvt(nvt)

    assert outcome.decision_code in (DecisionCode.AUTO_VORSCHLAG, DecisionCode.AUTO_FREIGABE_VORBEREITET)
    assert outcome.selected_ruleplan_id == "PLAN_A"
    assert nvt.decision is not None
    assert nvt.decision.selected_ruleplan_id == "PLAN_A"
    assert len(nvt.ruleplan_candidates) >= 1
    assert NvtStatus(nvt.status) == NvtStatus.NEEDS_REVIEW


def test_privatflaeche_persisted_with_null_ruleplan(session: Session, library: RulePlanLibrary) -> None:
    nvt = _make_nvt_with_env(session)
    nvt.environment.private_property = Ternary.YES
    session.flush()

    outcome = DecisionBuilder(session, library=library).decide_for_nvt(nvt)
    assert outcome.decision_code == DecisionCode.PRIVATFLAECHE
    assert nvt.decision.selected_ruleplan_id is None


def test_no_env_returns_nicht_beurteilbar(session: Session, library: RulePlanLibrary) -> None:
    project = ProjectRepo(session).create(
        ProjectCreate(name="P", contractor="F", ruleset_version="v1", vision_provider="mock")
    )
    nvt = Nvt(project_id=project.id, nvt_number="7107", warnings_json=[])
    session.add(nvt)
    session.flush()

    outcome = DecisionBuilder(session, library=library).decide_for_nvt(nvt)
    assert outcome.decision_code == DecisionCode.NICHT_BEURTEILBAR
    assert nvt.decision is None


def test_second_decide_skipped_without_force(session: Session, library: RulePlanLibrary) -> None:
    nvt = _make_nvt_with_env(session)
    b = DecisionBuilder(session, library=library)
    b.decide_for_nvt(nvt)
    outcome = b.decide_for_nvt(nvt)
    assert "existiert bereits" in outcome.warnings[0]

    outcome = b.decide_for_nvt(nvt, force=True)
    assert "existiert bereits" not in " ".join(outcome.warnings)
