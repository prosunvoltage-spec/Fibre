"""Sanity-Tests für die tatsächlich eingecheckten Metadaten unter /knowledge/.

Diese Tests laden die im Repo hinterlegten JSON-Dateien und prüfen, dass sie
konsistent, korrekt referenziert und ladbar sind. Sie decken damit den
Zustand nach ``scripts/bootstrap_knowledge.py`` ab.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.reference_cases import ReferenceCaseLibrary
from app.ruleplans import RulePlanLibrary

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"


@pytest.fixture(scope="module")
def reference_lib() -> ReferenceCaseLibrary:
    return ReferenceCaseLibrary(KNOWLEDGE_ROOT / "referenzfaelle").load()


@pytest.fixture(scope="module")
def ruleplan_lib() -> RulePlanLibrary:
    return RulePlanLibrary(KNOWLEDGE_ROOT / "regelplaene").load()


def test_all_reference_cases_loadable(reference_lib: ReferenceCaseLibrary) -> None:
    cases = reference_lib.all()
    assert len(cases) >= 25, f"weniger als 25 Referenzfälle gefunden: {len(cases)}"


def test_nvt_numbers_unique_and_sane(reference_lib: ReferenceCaseLibrary) -> None:
    numbers = [c.nvt_number for c in reference_lib.all()]
    assert len(numbers) == len(set(numbers)), "NVT-Nummern nicht eindeutig"
    for nr in numbers:
        assert nr.isdigit() and len(nr) == 4, f"Ungültige NVT-Nummer: {nr}"


def test_every_case_has_source_file(reference_lib: ReferenceCaseLibrary) -> None:
    for case in reference_lib:
        assert case.source_file, f"NVT {case.nvt_number}: source_file fehlt"


def test_source_pages_when_present_are_valid_ints(
    reference_lib: ReferenceCaseLibrary,
) -> None:
    for case in reference_lib:
        if case.source_page is not None:
            assert isinstance(case.source_page, int)
            assert case.source_page > 0


def test_known_reference_zuordnungen(reference_lib: ReferenceCaseLibrary) -> None:
    """Stichprobe für bekannte NVT — Regressionsschutz."""
    expected: dict[str, dict] = {
        "7107": {"ruleplan_label": "B2/2", "source_page": 11},
        "7116": {"ruleplan_label": "VZP1", "source_page": 31},
        "7124": {"ruleplan_label": "B1/2", "source_page": 46},
        "7103": {"ruleplan_label": "B1/15", "source_page": 5},
    }
    for nr, exp in expected.items():
        c = reference_lib.get(nr)
        assert c is not None, f"NVT {nr} fehlt"
        assert c.ruleplan_label == exp["ruleplan_label"]
        assert c.source_page == exp["source_page"]


def test_private_property_cases_recognised(reference_lib: ReferenceCaseLibrary) -> None:
    private = {c.nvt_number for c in reference_lib.private_property_cases()}
    # 7105/7106 Betriebsgelände, 7109 Privatfläche, 7113/7114 Privatgelände Stadtnetze
    assert {"7109", "7113", "7114"}.issubset(private)


def test_ruleplan_library_has_four_entries(ruleplan_lib: RulePlanLibrary) -> None:
    assert set(ruleplan_lib.ids()) == {"VZP1", "B1/2", "B2/2", "B1/15"}


def test_all_ruleplans_are_incomplete_initially(ruleplan_lib: RulePlanLibrary) -> None:
    """Solange Fachanwender die Metadaten nicht gepflegt hat, is_complete=False."""
    for entry in ruleplan_lib:
        assert entry.schema.is_complete is False, (
            f"{entry.schema.id} ist unerwartet as complete markiert; "
            "der Loader muss die Vollständigkeit selbst berechnen"
        )


def test_ruleplan_source_pages_53_to_56(ruleplan_lib: RulePlanLibrary) -> None:
    """Die 4 Regelpläne stammen aus dem Referenz-PDF-Seitenbereich 53-56."""
    pages = sorted(
        p for e in ruleplan_lib
        if (p := getattr(e.schema, "source_page", None)) is not None
        or (p := (_source_page_from_raw(e.schema.id))) is not None
    )
    # RulePlanSchema hat kein source_page-Feld direkt, aber wir prüfen indirekt
    # durch die Datei-Rohdaten:
    from json import loads

    for e in ruleplan_lib:
        dir_map = {"VZP1": "VZP1", "B1/2": "B1_2", "B2/2": "B2_2", "B1/15": "B1_15"}
        p = KNOWLEDGE_ROOT / "regelplaene" / dir_map[e.schema.id] / "metadata.json"
        raw = loads(p.read_text(encoding="utf-8"))
        assert raw["source_page"] in (53, 54, 55, 56)


def _source_page_from_raw(_id: str) -> None:  # helper stub for pages test
    return None
