"""Regressionstest gegen die 26 Roxel-Referenzfälle.

Wichtig: Der Test erwartet **nicht**, dass die Rule Engine denselben
Regelplan wählt wie die Referenz-VRA (die Zuordnung dort ist fachliches
Ermessen). Er prüft nur, dass die Engine:

- Privatflächen-Fälle in den PRIVATFLAECHE-Sonderpfad schickt
- Sackgassen-Fälle eine passende Warnung erzeugen
- Für alle Fälle KEINE ungerechtfertigte AUTO_FREIGABE ausgibt, solange
  die Regelplan-Metadaten unvollständig sind (is_complete=False)
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.enums import (
    DecisionCode,
    NvtPosition,
    RoadClass,
    Ternary,
)
from app.core.schemas import EnvironmentAnalysisSchema
from app.reference_cases import ReferenceCase, ReferenceCaseLibrary
from app.ruleplans import RulePlanLibrary
from app.rules import decide


@pytest.fixture(scope="module")
def reference_cases() -> list[ReferenceCase]:
    from app.config import get_settings

    lib = ReferenceCaseLibrary(get_settings().knowledge_path / "referenzfaelle").load()
    return lib.all()


@pytest.fixture(scope="module")
def ruleplans() -> RulePlanLibrary:
    from app.config import get_settings

    return RulePlanLibrary(get_settings().knowledge_path / "regelplaene").load()


def _synthetic_env_for(case: ReferenceCase) -> EnvironmentAnalysisSchema:
    """Baut eine minimale EnvironmentAnalysis aus dem Referenzfall-Label.

    In Phase 5+ würde diese Analyse aus dem echten Vision-Provider kommen.
    Für den Regressionstest reicht es, die spezifischen Attribute je Fall zu
    setzen (Privatfläche, Sackgasse …); der Rest bleibt UNKNOWN.
    """
    kw: dict = {"nvt_id": uuid4(), "data_completeness": Decimal("0.8")}

    if case.is_private_property():
        kw["private_property"] = Ternary.YES
        marker = (case.special_case or "").lower()
        if "stadtnetze" in marker or "stadtwerke" in marker or "betrieb" in marker:
            kw["business_property"] = Ternary.YES
            kw["nvt_position"] = NvtPosition.ON_BUSINESS_PREMISES
        return EnvironmentAnalysisSchema(**kw)

    # Sackgasse (7103)
    notes = (case.notes or "").lower()
    if "sackgasse" in notes:
        kw["cul_de_sac"] = Ternary.YES
        kw["road_class"] = RoadClass.SACKGASSE

    # generische innerorts-Situation
    kw.setdefault("road_present", Ternary.YES)
    kw.setdefault("sidewalk_present", Ternary.YES)
    kw.setdefault("cycleway_present", Ternary.NO)
    kw.setdefault("private_property", Ternary.NO)
    kw.setdefault("business_property", Ternary.NO)
    kw.setdefault("nvt_position", NvtPosition.AT_ROADSIDE)
    kw.setdefault("road_class", RoadClass.WOHNSTRASSE)
    return EnvironmentAnalysisSchema(**kw)


@pytest.mark.regression
def test_have_at_least_25_reference_cases(reference_cases: list[ReferenceCase]) -> None:
    assert len(reference_cases) >= 25


@pytest.mark.regression
def test_private_property_cases_get_privatflaeche_code(
    reference_cases: list[ReferenceCase], ruleplans: RulePlanLibrary
) -> None:
    expected_private = {"7109", "7113", "7114"}
    for case in reference_cases:
        if case.nvt_number not in expected_private:
            continue
        env = _synthetic_env_for(case)
        outcome = decide(env, ruleplans.all())
        assert outcome.code == DecisionCode.PRIVATFLAECHE, (
            f"NVT {case.nvt_number} sollte PRIVATFLAECHE ergeben, "
            f"bekam aber {outcome.code}"
        )
        assert outcome.selected_ruleplan_id is None


@pytest.mark.regression
def test_business_premises_also_privatflaeche(
    reference_cases: list[ReferenceCase], ruleplans: RulePlanLibrary
) -> None:
    for case in reference_cases:
        if case.nvt_number not in {"7105", "7106"}:
            continue
        env = _synthetic_env_for(case)
        outcome = decide(env, ruleplans.all())
        assert outcome.code == DecisionCode.PRIVATFLAECHE


@pytest.mark.regression
def test_cul_de_sac_triggers_warning(
    reference_cases: list[ReferenceCase], ruleplans: RulePlanLibrary
) -> None:
    case = next(c for c in reference_cases if c.nvt_number == "7103")
    env = _synthetic_env_for(case)
    outcome = decide(env, ruleplans.all())
    assert any("Sackgasse" in w for w in outcome.warnings)


@pytest.mark.regression
def test_no_auto_freigabe_from_generic_synthetic_env(
    reference_cases: list[ReferenceCase], ruleplans: RulePlanLibrary
) -> None:
    """Die generischen Synthetic-Envs dieses Tests setzen keine Fahrbahnbreite
    (remaining_roadway_ge liefert UNKNOWN), daher darf selbst der bereits
    gepflegte VZP1-Regelplan (siehe test_knowledge_bootstrap.py) hier nie zu
    AUTO_FREIGABE_VORBEREITET führen — die Voraussetzung bleibt offen."""
    for case in reference_cases:
        env = _synthetic_env_for(case)
        outcome = decide(env, ruleplans.all())
        assert outcome.code != DecisionCode.AUTO_FREIGABE_VORBEREITET, (
            f"NVT {case.nvt_number}: unerwartete AUTO_FREIGABE ohne "
            f"bestätigte Fahrbahnbreite (code={outcome.code})"
        )


@pytest.mark.regression
def test_every_case_produces_a_decision(
    reference_cases: list[ReferenceCase], ruleplans: RulePlanLibrary
) -> None:
    """Kein Referenzfall darf zu einem Exception-Zustand führen."""
    for case in reference_cases:
        env = _synthetic_env_for(case)
        outcome = decide(env, ruleplans.all())
        assert outcome.code in DecisionCode, f"NVT {case.nvt_number}: unbekannter Code"
        # human_review_required bleibt in Phase 6 immer True (keine Auto-Freigabe)
        assert outcome.human_review_required is True
