"""Tests für RulePlanLibrary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ruleplans import RulePlanLibrary, RulePlanLoadError


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_empty_root(tmp_path: Path) -> None:
    lib = RulePlanLibrary(tmp_path / "regelplaene").load()
    assert list(lib) == []
    assert lib.ids() == []


def test_load_minimal_incomplete(tmp_path: Path) -> None:
    _write(
        tmp_path / "B1_2" / "metadata.json",
        {
            "id": "B1/2",
            "name": "Regelplan B I/2",
            "quelle": "RSA 21",
        },
    )
    lib = RulePlanLibrary(tmp_path).load()
    entry = lib.get("B1/2")
    assert entry is not None
    # Pflichtfelder leer → is_complete = False + Issues
    assert entry.schema.is_complete is False
    assert lib.incomplete_ids() == ["B1/2"]
    assert lib.complete_ids() == []
    fields = {i.field for i in entry.issues}
    assert "verkehrsraum" in fields
    assert "geeignet_fuer" in fields
    assert "voraussetzungen" in fields
    assert "allowed_symbols" in fields


def test_source_document_missing_is_issue(tmp_path: Path) -> None:
    _write(
        tmp_path / "B1_2" / "metadata.json",
        {
            "id": "B1/2",
            "name": "B1/2",
            "quelle": "RSA 21",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [{"predicate": "road_affected", "value": True}],
            "allowed_symbols": ["leitbake"],
            "voraussetzungen": [
                {
                    "condition": "irgendwas",
                    "source_document": "",  # leer!
                    "source_reference": "x",
                }
            ],
        },
    )
    lib = RulePlanLibrary(tmp_path).load()
    entry = lib.get("B1/2")
    assert entry is not None
    fields = {i.field for i in entry.issues}
    assert "voraussetzungen[0].source_document" in fields


def test_full_metadata_can_be_complete(tmp_path: Path) -> None:
    # Wenn Binaries als Dummys existieren
    (tmp_path / "B1_2" / "plan.pdf").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "B1_2" / "plan.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "B1_2" / "preview.png").write_bytes(b"\x89PNG")
    _write(
        tmp_path / "B1_2" / "metadata.json",
        {
            "id": "B1/2",
            "name": "Regelplan B I/2 modifiziert",
            "quelle": "RSA 21 Teil D",
            "version": "08.21",
            "beschreibung": "…",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [{"predicate": "road_affected", "value": True}],
            "voraussetzungen": [
                {
                    "condition": "Restfahrbahnbreite ≥ 3,00 m",
                    "source_document": "Auflagen Stadt Münster",
                    "source_reference": "Standardauflage §3",
                }
            ],
            "ausschlusskriterien": [
                {
                    "condition": "Kreuzung im Absperrbereich",
                    "source_document": "RSA 21 Teil D",
                    "source_reference": "2.4.3",
                }
            ],
            "allowed_symbols": ["leitbake", "warnbake"],
        },
    )
    lib = RulePlanLibrary(tmp_path).load()
    entry = lib.get("B1/2")
    assert entry is not None
    assert entry.schema.is_complete is True
    assert lib.complete_ids() == ["B1/2"]
    assert entry.schema.revision_hash != ""


def test_invalid_json_raises(tmp_path: Path) -> None:
    (tmp_path / "X" / "metadata.json").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "X" / "metadata.json").write_text("nicht valides json{", encoding="utf-8")
    with pytest.raises(RulePlanLoadError):
        RulePlanLibrary(tmp_path).load()
