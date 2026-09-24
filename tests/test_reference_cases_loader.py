"""Tests für ReferenceCaseLibrary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reference_cases import ReferenceCaseLibrary, ReferenceCaseLoadError


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_empty_root(tmp_path: Path) -> None:
    lib = ReferenceCaseLibrary(tmp_path).load()
    assert list(lib) == []


def test_load_basic(tmp_path: Path) -> None:
    _write(
        tmp_path / "NVT_7107" / "nvt.json",
        {
            "nvt_number": "7107",
            "source_file": "roxel.pdf",
            "source_page": 11,
            "address": {"street": "Roxeler Straße", "house_number": "579"},
            "ruleplan_label": "B2/2",
        },
    )
    lib = ReferenceCaseLibrary(tmp_path).load()
    case = lib.get("7107")
    assert case is not None
    assert case.address_street == "Roxeler Straße"
    assert case.ruleplan_label == "B2/2"
    assert case.source_page == 11
    assert case.kind == "reference"


def test_missing_nvt_number_raises(tmp_path: Path) -> None:
    _write(tmp_path / "NVT_X" / "nvt.json", {"source_file": "x.pdf"})
    with pytest.raises(ReferenceCaseLoadError):
        ReferenceCaseLibrary(tmp_path).load()


def test_missing_source_file_raises(tmp_path: Path) -> None:
    _write(tmp_path / "NVT_X" / "nvt.json", {"nvt_number": "X"})
    with pytest.raises(ReferenceCaseLoadError):
        ReferenceCaseLibrary(tmp_path).load()


def test_private_property_detection(tmp_path: Path) -> None:
    _write(
        tmp_path / "NVT_7109" / "nvt.json",
        {
            "nvt_number": "7109",
            "source_file": "roxel.pdf",
            "special_case": "Privatfläche",
        },
    )
    _write(
        tmp_path / "NVT_7113" / "nvt.json",
        {
            "nvt_number": "7113",
            "source_file": "roxel.pdf",
            "special_case": "Privatgelände der Stadtnetze Münster",
        },
    )
    _write(
        tmp_path / "NVT_7107" / "nvt.json",
        {
            "nvt_number": "7107",
            "source_file": "roxel.pdf",
            "ruleplan_label": "B2/2",
        },
    )
    lib = ReferenceCaseLibrary(tmp_path).load()
    private = {c.nvt_number for c in lib.private_property_cases()}
    assert private == {"7109", "7113"}


def test_with_ruleplan_filter(tmp_path: Path) -> None:
    for nr, plan in [("7107", "B2/2"), ("7116", "VZP1"), ("7117", "VZP1")]:
        _write(
            tmp_path / f"NVT_{nr}" / "nvt.json",
            {"nvt_number": nr, "source_file": "x.pdf", "ruleplan_label": plan},
        )
    lib = ReferenceCaseLibrary(tmp_path).load()
    vzp1 = {c.nvt_number for c in lib.with_ruleplan("VZP1")}
    assert vzp1 == {"7116", "7117"}


def test_invalid_json_raises(tmp_path: Path) -> None:
    (tmp_path / "NVT_X" / "nvt.json").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "NVT_X" / "nvt.json").write_text("{invalid", encoding="utf-8")
    with pytest.raises(ReferenceCaseLoadError):
        ReferenceCaseLibrary(tmp_path).load()
