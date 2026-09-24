"""Tests für die QA-Prüfliste."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core.enums import (
    DecisionCode,
    NvtStatus,
    PhotoKind,
    ReviewAction,
    Ternary,
)
from app.core.models import (
    Decision,
    EnvironmentAnalysis,
    Nvt,
    Photo,
    Review,
    Visualization,
)
from app.core.repositories import ProjectRepo
from app.core.schemas import ProjectCreate
from app.ruleplans import RulePlanLibrary
from app.validation import run_qa_gate


@pytest.fixture()
def library(tmp_path: Path) -> RulePlanLibrary:
    root = tmp_path / "rp"
    (root / "B1_2").mkdir(parents=True)
    (root / "B1_2" / "metadata.json").write_text(
        json.dumps({
            "id": "B1/2", "name": "B1/2", "quelle": "T",
            "verkehrsraum": ["innerorts"],
            "geeignet_fuer": [{"predicate": "has_sidewalk", "value": "yes"}],
            "voraussetzungen": [],
            "ausschlusskriterien": [],
            "allowed_symbols": ["leitbake"],
        })
    )
    (root / "B1_2" / "plan.pdf").write_bytes(b"%PDF")
    (root / "B1_2" / "preview.png").write_bytes(b"\x89PNG")
    return RulePlanLibrary(root).load()


def _make_project(session: Session):  # type: ignore[no-untyped-def]
    return ProjectRepo(session).create(
        ProjectCreate(name="P", contractor="F", ruleset_version="v1", vision_provider="mock")
    )


def _full_nvt(session: Session, project, nvt_number: str = "7107", *, with_review: bool = True) -> Nvt:  # type: ignore[no-untyped-def]
    nvt = Nvt(
        project_id=project.id,
        nvt_number=nvt_number,
        warnings_json=[],
        address_json={"street": "Musterstr", "house_number": "1", "postal_code": "48161", "city": "Münster"},
        status=NvtStatus.APPROVED,
    )
    session.add(nvt)
    session.flush()

    photo = Photo(
        nvt_id=nvt.id, filename="a.jpg", stored_path="/tmp/a.jpg",
        mime_type="image/jpeg", width=1, height=1, sha256="a" * 64,
        kind=PhotoKind.ORIGINAL,
    )
    nvt.photos.append(photo)
    session.flush()  # photo.id auflösen für viz.base_photo_id

    env = EnvironmentAnalysis(
        nvt_id=nvt.id, road_present=Ternary.YES, sidewalk_present=Ternary.YES,
        vision_confidence=Decimal("0.9"), data_completeness=Decimal("1"),
        model_id="mock", prompt_hash="x",
    )
    nvt.environment = env

    decision = Decision(
        nvt_id=nvt.id, selected_ruleplan_id="B1/2", code=DecisionCode.AUTO_VORSCHLAG,
        vision_confidence=Decimal("0.9"), rule_confidence=Decimal("0.85"),
        data_completeness=Decimal("1"), human_review_required=True,
        reasons=["ok"], warnings=[], ruleset_version="v1",
    )
    nvt.decision = decision

    viz = Visualization(nvt_id=nvt.id, base_photo_id=photo.id, symbols=[], shapes=[])
    nvt.visualization = viz

    if with_review:
        nvt.reviews.append(
            Review(
                nvt_id=nvt.id, reviewer="user", action=ReviewAction.APPROVED,
                comment="ok", before={}, after={}, timestamp=datetime.now(UTC),
            )
        )
    session.flush()
    return nvt


def test_qa_gate_passes_for_complete_nvt(session: Session, library: RulePlanLibrary) -> None:
    project = _make_project(session)
    _full_nvt(session, project)

    from app.core.repositories import NvtRepo
    report = run_qa_gate(project, NvtRepo(session).list_for_project(project.id), library)
    assert report.passed, [f.__dict__ for f in report.failures]


def test_qa_gate_fails_without_photo(session: Session, library: RulePlanLibrary) -> None:
    project = _make_project(session)
    nvt = _full_nvt(session, project)
    photo = nvt.photos[0]
    nvt.photos.remove(photo)
    session.delete(photo)
    session.flush()

    from app.core.repositories import NvtRepo
    report = run_qa_gate(project, NvtRepo(session).list_for_project(project.id), library)
    assert not report.passed
    assert any(f.check == "no_photo" for f in report.failures)


def test_qa_gate_fails_without_approved_review(session: Session, library: RulePlanLibrary) -> None:
    project = _make_project(session)
    _full_nvt(session, project, with_review=False)

    from app.core.repositories import NvtRepo
    report = run_qa_gate(project, NvtRepo(session).list_for_project(project.id), library)
    assert not report.passed
    assert any(f.check == "not_approved" for f in report.failures)


def test_qa_gate_allows_privatflaeche_without_visualization(
    session: Session, library: RulePlanLibrary
) -> None:
    project = _make_project(session)
    nvt = _full_nvt(session, project)
    # Als Privatfläche umbauen
    nvt.decision.code = DecisionCode.PRIVATFLAECHE
    nvt.decision.selected_ruleplan_id = None
    session.delete(nvt.visualization)
    nvt.visualization = None
    session.flush()

    from app.core.repositories import NvtRepo
    report = run_qa_gate(project, NvtRepo(session).list_for_project(project.id), library)
    assert report.passed, [f.__dict__ for f in report.failures]


def test_qa_gate_dry_run_ignores_review(session: Session, library: RulePlanLibrary) -> None:
    project = _make_project(session)
    nvt = _full_nvt(session, project, with_review=False)
    nvt.status = NvtStatus.NEEDS_REVIEW
    session.flush()

    from app.core.repositories import NvtRepo
    report = run_qa_gate(
        project,
        NvtRepo(session).list_for_project(project.id),
        library,
        require_review=False,
    )
    assert report.passed
