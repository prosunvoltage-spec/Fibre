"""Tests für Symbol-Registry, Renderer und Proposer."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from app.core.enums import (
    NvtPosition,
    OverlaySymbolType,
    Ternary,
)
from app.core.schemas import (
    EnvironmentAnalysisSchema,
    OverlayPointSchema,
    OverlayShapeSchema,
    OverlaySymbolSchema,
    VisualizationSchema,
)
from app.ruleplans import RulePlanLibrary
from app.visualization.proposer import propose_visualization
from app.visualization.renderer import RenderError, render_overlay
from app.visualization.symbols import SymbolRegistry


@pytest.fixture(scope="module")
def real_registry() -> SymbolRegistry:
    """Nimmt die tatsächlich erzeugten Symbole aus data/symbols/."""
    from app.config import get_settings

    return SymbolRegistry(get_settings().storage_path / "symbols")


@pytest.fixture()
def base_photo(tmp_path: Path) -> Path:
    p = tmp_path / "base.jpg"
    Image.new("RGB", (800, 600), color=(180, 180, 180)).save(p, "JPEG")
    return p


def test_registry_finds_all_ten_symbols(real_registry: SymbolRegistry) -> None:
    for t in OverlaySymbolType:
        assert real_registry.available(t), f"Symbol {t.value} fehlt in data/symbols/"


def test_render_overlay_writes_output(base_photo: Path, real_registry: SymbolRegistry, tmp_path: Path) -> None:
    viz = VisualizationSchema(
        nvt_id=uuid4(),
        base_photo_id=uuid4(),
        symbols=[
            OverlaySymbolSchema(
                type=OverlaySymbolType.LEITBAKE,
                x=Decimal("0.3"), y=Decimal("0.6"),
            ),
            OverlaySymbolSchema(
                type=OverlaySymbolType.LEITBAKE,
                x=Decimal("0.7"), y=Decimal("0.6"),
            ),
        ],
        shapes=[
            OverlayShapeSchema(
                kind="polygon",
                points=[
                    OverlayPointSchema(x=Decimal("0.25"), y=Decimal("0.55")),
                    OverlayPointSchema(x=Decimal("0.75"), y=Decimal("0.55")),
                    OverlayPointSchema(x=Decimal("0.75"), y=Decimal("0.85")),
                    OverlayPointSchema(x=Decimal("0.25"), y=Decimal("0.85")),
                ],
            ),
        ],
    )
    out = tmp_path / "rendered.jpg"
    result = render_overlay(
        base_photo_path=base_photo, visualization=viz, output_path=out,
        registry=real_registry,
    )
    assert out.is_file()
    assert result.rendered_symbol_count == 2
    assert result.rendered_shape_count == 1
    # Ausgabe hat gleiche Größe wie Original
    img = Image.open(out)
    assert img.size == (800, 600)


def test_render_missing_base_photo_raises(tmp_path: Path, real_registry: SymbolRegistry) -> None:
    viz = VisualizationSchema(nvt_id=uuid4(), base_photo_id=uuid4(), symbols=[], shapes=[])
    with pytest.raises(RenderError):
        render_overlay(
            base_photo_path=tmp_path / "nope.jpg",
            visualization=viz,
            output_path=tmp_path / "out.jpg",
            registry=real_registry,
        )


def test_proposer_produces_two_leitbaken_by_default(tmp_path: Path) -> None:
    root = tmp_path / "rp"
    (root / "PLAN").mkdir(parents=True)
    (root / "PLAN" / "metadata.json").write_text(
        json.dumps({
            "id": "PLAN", "name": "Plan", "quelle": "T",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [{"predicate": "has_sidewalk", "value": "yes"}],
            "voraussetzungen": [],
            "ausschlusskriterien": [],
            "allowed_symbols": ["leitbake", "warnbake"],
        })
    )
    (root / "PLAN" / "plan.pdf").write_bytes(b"%PDF")
    (root / "PLAN" / "preview.png").write_bytes(b"\x89PNG")
    lib = RulePlanLibrary(root).load()

    env = EnvironmentAnalysisSchema(
        nvt_id=uuid4(),
        road_present=Ternary.YES,
        sidewalk_present=Ternary.YES,
        nvt_position=NvtPosition.AT_ROADSIDE,
    )
    result = propose_visualization(
        nvt_id=uuid4(), base_photo_id=uuid4(), env=env, ruleplan=lib.get("PLAN"),
    )
    assert result.has_proposal()
    assert result.visualization is not None
    # Zwei Leitbaken
    types = [s.type for s in result.visualization.symbols]
    assert types.count(OverlaySymbolType.LEITBAKE) == 2


def test_proposer_privatflaeche_no_visualization() -> None:
    env = EnvironmentAnalysisSchema(nvt_id=uuid4(), private_property=Ternary.YES)
    result = propose_visualization(
        nvt_id=uuid4(), base_photo_id=uuid4(), env=env, ruleplan=None,
    )
    assert not result.has_proposal()
    assert result.reason is not None
    assert "Privat" in result.reason


def test_proposer_without_ruleplan_uses_fallback_set() -> None:
    env = EnvironmentAnalysisSchema(
        nvt_id=uuid4(),
        sidewalk_present=Ternary.YES,
        nvt_position=NvtPosition.AT_ROADSIDE,
    )
    result = propose_visualization(
        nvt_id=uuid4(), base_photo_id=uuid4(), env=env, ruleplan=None,
    )
    assert result.has_proposal()
    assert any("Kein Regelplan gewählt" in w for w in result.warnings)


def test_proposer_respects_allowed_symbols(tmp_path: Path) -> None:
    """Ist LEITBAKE nicht in allowed_symbols, wird sie nicht vorgeschlagen."""
    root = tmp_path / "rp"
    (root / "PLAN").mkdir(parents=True)
    (root / "PLAN" / "metadata.json").write_text(
        json.dumps({
            "id": "PLAN", "name": "Plan", "quelle": "T",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [{"predicate": "has_sidewalk", "value": "yes"}],
            "voraussetzungen": [],
            "ausschlusskriterien": [],
            "allowed_symbols": ["absperrschranke"],  # weder leitbake noch warnbake
        })
    )
    (root / "PLAN" / "plan.pdf").write_bytes(b"%PDF")
    (root / "PLAN" / "preview.png").write_bytes(b"\x89PNG")
    lib = RulePlanLibrary(root).load()

    env = EnvironmentAnalysisSchema(
        nvt_id=uuid4(),
        sidewalk_present=Ternary.YES,
        nvt_position=NvtPosition.AT_ROADSIDE,
    )
    result = propose_visualization(
        nvt_id=uuid4(), base_photo_id=uuid4(), env=env, ruleplan=lib.get("PLAN"),
    )
    types = [s.type for s in (result.visualization.symbols if result.visualization else [])]
    assert OverlaySymbolType.LEITBAKE not in types
    assert OverlaySymbolType.WARNBAKE not in types
