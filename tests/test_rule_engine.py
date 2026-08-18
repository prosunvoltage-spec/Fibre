"""Tests für die Rule Engine als Ganzes."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import json

import pytest

from app.core.enums import (
    DecisionCode,
    NvtPosition,
    RoadClass,
    Ternary,
)
from app.core.schemas import EnvironmentAnalysisSchema, WorkAreaSchema
from app.ruleplans import RulePlanLibrary
from app.rules import decide


def _env(**overrides) -> EnvironmentAnalysisSchema:  # type: ignore[no-untyped-def]
    # Default: data_completeness=1, damit Tests nicht am Vollständigkeits-Guard
    # scheitern. Wer den Guard testen will, überschreibt explizit.
    overrides.setdefault("data_completeness", Decimal("1"))
    return EnvironmentAnalysisSchema(nvt_id=uuid4(), **overrides)


@pytest.fixture()
def library(tmp_path: Path) -> RulePlanLibrary:
    """Zwei erfundene Regelpläne mit sinnvoll gepflegten Metadaten."""
    root = tmp_path / "regelplaene"
    _write(
        root / "PLAN_A" / "metadata.json",
        {
            "id": "PLAN_A",
            "name": "Plan A — Gehwegseite",
            "quelle": "Test",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [
                {"predicate": "has_sidewalk", "value": "yes"},
                {"predicate": "has_cycleway", "value": "no"},
            ],
            "voraussetzungen": [
                {
                    "condition": "Restfahrbahnbreite ≥ 3,00 m",
                    "machine_predicate": "remaining_roadway_ge",
                    "args": {"min_m": 3.0},
                    "source_document": "Auflagen Test",
                    "source_reference": "§1",
                }
            ],
            "ausschlusskriterien": [],
            "allowed_symbols": ["leitbake"],
        },
    )
    _write(
        root / "PLAN_B" / "metadata.json",
        {
            "id": "PLAN_B",
            "name": "Plan B — Vollsperrung",
            "quelle": "Test",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [
                {"predicate": "is_cul_de_sac", "value": "yes"},
            ],
            "voraussetzungen": [],
            "ausschlusskriterien": [],
            "allowed_symbols": ["absperrschranke"],
        },
    )
    # Dummy-Binaries, damit is_complete=True möglich wird
    (root / "PLAN_A" / "plan.pdf").write_bytes(b"%PDF-1.4")
    (root / "PLAN_A" / "preview.png").write_bytes(b"\x89PNG")
    (root / "PLAN_B" / "plan.pdf").write_bytes(b"%PDF-1.4")
    (root / "PLAN_B" / "preview.png").write_bytes(b"\x89PNG")

    return RulePlanLibrary(root).load()


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_privatflaeche_short_circuits(library: RulePlanLibrary) -> None:
    env = _env(private_property=Ternary.YES)
    o = decide(env, library.all())
    assert o.code == DecisionCode.PRIVATFLAECHE
    assert o.selected_ruleplan_id is None
    assert o.human_review_required is True


def test_business_area_short_circuits(library: RulePlanLibrary) -> None:
    env = _env(
        business_property=Ternary.YES,
        nvt_position=NvtPosition.ON_BUSINESS_PREMISES,
    )
    o = decide(env, library.all())
    assert o.code == DecisionCode.PRIVATFLAECHE


def test_low_completeness_triggers_manual_review(library: RulePlanLibrary) -> None:
    env = _env(data_completeness=Decimal("0.2"))
    o = decide(env, library.all(), critical_completeness_threshold=Decimal("0.5"))
    assert o.code == DecisionCode.MANUELLE_PRUEFUNG


def test_empty_library_gives_regelplan_nicht_gefunden(library: RulePlanLibrary) -> None:
    env = _env(sidewalk_present=Ternary.YES, road_present=Ternary.YES)
    o = decide(env, ruleplans=[])
    assert o.code == DecisionCode.REGELPLAN_NICHT_GEFUNDEN


def test_matching_plan_gives_auto_vorschlag(library: RulePlanLibrary) -> None:
    env = _env(
        # Alle 19 Felder gesetzt (data_completeness passt später sowieso nicht auf 1)
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
        nvt_position=NvtPosition.AT_ROADSIDE,
        road_class=RoadClass.WOHNSTRASSE,
        vision_confidence=Decimal("0.9"),
    )
    o = decide(env, library.all())
    # data_completeness kommt aus Schema, weil wir die manuell setzen können
    assert o.code in (DecisionCode.AUTO_VORSCHLAG, DecisionCode.AUTO_FREIGABE_VORBEREITET)
    assert o.selected_ruleplan_id == "PLAN_A"
    assert o.human_review_required is True


def test_no_matching_plan_gives_regelplan_nicht_gefunden(library: RulePlanLibrary) -> None:
    env = _env(
        # Keine Sackgasse, kein Gehweg → weder A noch B matcht
        road_present=Ternary.YES,
        sidewalk_present=Ternary.NO,
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
        nvt_position=NvtPosition.AT_ROADSIDE,
        road_class=RoadClass.HAUPTVERKEHR,
    )
    o = decide(env, library.all())
    assert o.code == DecisionCode.REGELPLAN_NICHT_GEFUNDEN


def test_incomplete_ruleplan_never_auto_freigabe(tmp_path: Path) -> None:
    """Regelpläne mit is_complete=False dürfen keine Auto-Freigabe auslösen."""
    root = tmp_path / "regelplaene"
    _write(
        root / "PLAN_X" / "metadata.json",
        {
            "id": "PLAN_X",
            "name": "Unvollständig",
            "quelle": "T",
            "geeignet_fuer": [{"predicate": "has_sidewalk", "value": "yes"}],
            # Keine voraussetzungen, allowed_symbols, verkehrsraum → is_complete=False
        },
    )
    lib = RulePlanLibrary(root).load()
    assert lib.get("PLAN_X").schema.is_complete is False

    env = _env(
        road_present=Ternary.YES, sidewalk_present=Ternary.YES,
        cycleway_present=Ternary.NO, shared_cycle_footway_present=Ternary.NO,
        parking_lane_present=Ternary.NO, seiten_streifen_present=Ternary.NO,
        private_property=Ternary.NO, business_property=Ternary.NO,
        driveway_present=Ternary.NO, intersection_present=Ternary.NO,
        junction_present=Ternary.NO, cul_de_sac=Ternary.NO,
        curve_present=Ternary.NO, bus_stop_nearby=Ternary.NO,
        fire_access=Ternary.NO, parked_vehicles_in_workarea=Ternary.NO,
        sight_relations_affected=Ternary.NO,
        nvt_position=NvtPosition.AT_ROADSIDE, road_class=RoadClass.WOHNSTRASSE,
        vision_confidence=Decimal("0.95"),
    )
    o = decide(env, lib.all(),
              auto_approve_rule_conf=Decimal("0.9"),
              auto_approve_completeness=Decimal("0.5"))
    assert o.code == DecisionCode.AUTO_VORSCHLAG  # niemals AUTO_FREIGABE_VORBEREITET
    assert o.rule_confidence <= Decimal("0.5")


def test_contradictions_trigger_manual_review(library: RulePlanLibrary) -> None:
    env = _env(
        sidewalk_present=Ternary.YES,
        contradictions=["cycleway_present: yes/no-Widerspruch"],
    )
    o = decide(env, library.all())
    assert o.code == DecisionCode.MANUELLE_PRUEFUNG


def test_warnings_collected_for_intersection(library: RulePlanLibrary) -> None:
    env = _env(
        road_present=Ternary.YES, sidewalk_present=Ternary.YES,
        cycleway_present=Ternary.NO, shared_cycle_footway_present=Ternary.NO,
        parking_lane_present=Ternary.NO, seiten_streifen_present=Ternary.NO,
        private_property=Ternary.NO, business_property=Ternary.NO,
        driveway_present=Ternary.NO,
        intersection_present=Ternary.YES,  # ← Warnung
        junction_present=Ternary.NO, cul_de_sac=Ternary.NO,
        curve_present=Ternary.NO, bus_stop_nearby=Ternary.NO,
        fire_access=Ternary.NO, parked_vehicles_in_workarea=Ternary.NO,
        sight_relations_affected=Ternary.NO,
        nvt_position=NvtPosition.AT_ROADSIDE, road_class=RoadClass.WOHNSTRASSE,
    )
    o = decide(env, library.all())
    assert any("Kreuzung" in w for w in o.warnings)


def test_tie_between_top_candidates(library: RulePlanLibrary, tmp_path: Path) -> None:
    """Wenn zwei Kandidaten fast identisch matchen → WIDERSPRUCH."""
    # Wir vergleichen zwei Regelpläne, die beide auf sidewalk=yes matchen
    root = tmp_path / "regelplaene2"
    for pid in ("PLAN_C", "PLAN_D"):
        _write(
            root / pid / "metadata.json",
            {
                "id": pid,
                "name": pid,
                "quelle": "T",
                "verkehrsraum": ["innerorts"],
                "geeignet_fuer": [{"predicate": "has_sidewalk", "value": "yes"}],
                "voraussetzungen": [],
                "ausschlusskriterien": [],
                "allowed_symbols": ["leitbake"],
            },
        )
        (root / pid / "plan.pdf").write_bytes(b"%PDF")
        (root / pid / "preview.png").write_bytes(b"\x89PNG")
    lib = RulePlanLibrary(root).load()
    env = _env(
        sidewalk_present=Ternary.YES, road_present=Ternary.YES,
        cycleway_present=Ternary.NO,
        # setz die verbleibenden 15 auf NO für completeness
        **{
            f: Ternary.NO for f in [
                "shared_cycle_footway_present", "parking_lane_present",
                "seiten_streifen_present", "private_property", "business_property",
                "driveway_present", "intersection_present", "junction_present",
                "cul_de_sac", "curve_present", "bus_stop_nearby", "fire_access",
                "parked_vehicles_in_workarea", "sight_relations_affected",
            ]
        },
        nvt_position=NvtPosition.AT_ROADSIDE, road_class=RoadClass.WOHNSTRASSE,
    )
    o = decide(env, lib.all())
    assert o.code == DecisionCode.WIDERSPRUCH
    assert o.selected_ruleplan_id is None
