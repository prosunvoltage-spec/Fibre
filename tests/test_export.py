"""Tests für Word-Builder, HTML-Report und Export-Service."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image
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
from app.core.repositories import AuditRepo, NvtRepo, ProjectRepo
from app.core.schemas import ProjectCreate
from app.core.services import ExportService
from app.documents import build_word_anlage
from app.documents.html_report import build_html_report
from app.ruleplans import RulePlanLibrary


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
    Image.new("RGB", (200, 200), color="white").save(root / "B1_2" / "preview.png", "PNG")
    return RulePlanLibrary(root).load()


def _make_full_project_with_two_nvts(session: Session, tmp_path: Path):  # type: ignore[no-untyped-def]
    project = ProjectRepo(session).create(
        ProjectCreate(
            name="Roxel Test", contractor="Helder Santos GmbH",
            ruleset_version="v1", vision_provider="mock",
            period_start=date(2026, 7, 3), period_end=date(2026, 8, 15),
            location_label="Münster-Roxel",
        )
    )
    for i, nvt_number in enumerate(("7107", "7124")):
        nvt = Nvt(
            project_id=project.id, nvt_number=nvt_number, warnings_json=[],
            address_json={"street": "Musterstr", "house_number": nvt_number[-2:],
                          "postal_code": "48161", "city": "Münster"},
            status=NvtStatus.APPROVED,
        )
        session.add(nvt)
        session.flush()

        # Farbwert variiert pro NVT, damit python-docx die Bilder nicht als
        # byte-identisch dedupliziert (das würde Testaussagen verfälschen).
        base_color = 190 + i * 20

        photo_path = tmp_path / f"NVT_{nvt_number}.jpg"
        Image.new("RGB", (800, 600), color=(base_color, base_color, base_color)).save(photo_path, "JPEG")
        photo = Photo(
            nvt_id=nvt.id, filename=photo_path.name, stored_path=str(photo_path),
            mime_type="image/jpeg", width=800, height=600, sha256=nvt_number * 8 + "a" * 32,
            kind=PhotoKind.ORIGINAL,
        )
        nvt.photos.append(photo)
        session.flush()

        env = EnvironmentAnalysis(
            nvt_id=nvt.id, road_present=Ternary.YES, sidewalk_present=Ternary.YES,
            cycleway_present=Ternary.NO,
            vision_confidence=Decimal("0.9"), data_completeness=Decimal("1"),
            model_id="mock", prompt_hash="x",
            raw_provider_output={"road_present": "yes"},
        )
        nvt.environment = env

        decision = Decision(
            nvt_id=nvt.id, selected_ruleplan_id="B1/2", code=DecisionCode.AUTO_VORSCHLAG,
            vision_confidence=Decimal("0.9"), rule_confidence=Decimal("0.85"),
            data_completeness=Decimal("1"), human_review_required=True,
            reasons=[f"Bester Kandidat B1/2 für NVT {nvt_number}"],
            warnings=[], ruleset_version="v1",
            trace_json={"top_score": "0.85"},
        )
        nvt.decision = decision

        # Rendered photo als PROPOSAL
        rendered_path = tmp_path / f"NVT_{nvt_number}_proposal.jpg"
        Image.new("RGB", (800, 600), color=(base_color + 5, base_color + 5, base_color + 5)).save(rendered_path, "JPEG")
        rendered = Photo(
            nvt_id=nvt.id, filename=rendered_path.name, stored_path=str(rendered_path),
            mime_type="image/jpeg", width=800, height=600,
            sha256=nvt_number * 8 + "b" * 32,
            kind=PhotoKind.PROPOSAL,
        )
        nvt.photos.append(rendered)
        session.flush()

        viz = Visualization(nvt_id=nvt.id, base_photo_id=photo.id,
                            rendered_photo_id=rendered.id, symbols=[], shapes=[])
        nvt.visualization = viz

        nvt.reviews.append(Review(
            nvt_id=nvt.id, reviewer="tester", action=ReviewAction.APPROVED,
            comment="ok", before={}, after={}, timestamp=datetime.now(UTC),
        ))
    session.flush()
    return project


def test_word_builder_writes_valid_docx(session: Session, tmp_path: Path, library: RulePlanLibrary) -> None:
    project = _make_full_project_with_two_nvts(session, tmp_path)
    nvts = NvtRepo(session).list_for_project(project.id)
    out = tmp_path / "vra.docx"

    result = build_word_anlage(project, nvts, library, out)
    assert out.is_file()
    assert len(result.included_nvt_ids) == 2
    # Docx ist ein ZIP-Container
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "word/document.xml" in names
        # 2 Original + 2 Proposal + 2 Regelplan-Preview = 6 Bilder erwartet
        media = [n for n in names if n.startswith("word/media/")]
        assert len(media) >= 4


def test_word_export_contains_nvt_numbers(session: Session, tmp_path: Path, library: RulePlanLibrary) -> None:
    project = _make_full_project_with_two_nvts(session, tmp_path)
    nvts = NvtRepo(session).list_for_project(project.id)
    out = tmp_path / "vra.docx"
    build_word_anlage(project, nvts, library, out)

    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                text += "\n" + cell.text
    assert "7107" in text
    assert "7124" in text
    assert "TECHNISCHE UNTERLAGEN" in text
    # Verbotene Inhalte im Word (Halluzinations-Schutz):
    assert "vision_confidence" not in text.lower()
    assert "prompt_hash" not in text.lower()
    assert "raw_provider_output" not in text.lower()


def test_html_report_contains_debug_info(session: Session, tmp_path: Path, library: RulePlanLibrary) -> None:
    project = _make_full_project_with_two_nvts(session, tmp_path)
    nvts = NvtRepo(session).list_for_project(project.id)
    out = tmp_path / "report.html"
    audit = AuditRepo(session)
    build_html_report(project, nvts, audit, out)

    content = out.read_text(encoding="utf-8")
    assert "Interner Prüfbericht" in content
    assert "7107" in content
    assert "vision_confidence" in content
    assert "raw_provider_output" in content
    assert "NICHT der Behörde" in content


def test_export_service_writes_word_and_html(session: Session, tmp_path: Path, library: RulePlanLibrary) -> None:
    from app.config import get_settings

    settings = get_settings()
    # Storage temporär umleiten
    original = settings.storage_path
    object.__setattr__(settings, "storage_path", tmp_path / "storage")
    try:
        project = _make_full_project_with_two_nvts(session, tmp_path)
        service = ExportService(session, library=library, storage_root=settings.storage_path, user="tester")
        summary = service.export_project(project)

        assert summary.passed is True
        assert summary.docx_path is not None
        assert summary.html_report_path is not None
        assert Path(summary.docx_path).is_file()
        assert Path(summary.html_report_path).is_file()
    finally:
        object.__setattr__(settings, "storage_path", original)


def test_export_dry_run_reports_gate_only(session: Session, tmp_path: Path, library: RulePlanLibrary) -> None:
    project = _make_full_project_with_two_nvts(session, tmp_path)
    service = ExportService(session, library=library, storage_root=tmp_path / "storage")
    summary = service.export_project(project, dry_run=True)
    assert summary.passed is True
    assert summary.docx_path is None


def test_export_blocked_when_qa_fails(session: Session, tmp_path: Path, library: RulePlanLibrary) -> None:
    project = _make_full_project_with_two_nvts(session, tmp_path)
    # Review entfernen → QA-Gate soll blocken
    for nvt in NvtRepo(session).list_for_project(project.id):
        for r in list(nvt.reviews):
            nvt.reviews.remove(r)
            session.delete(r)
    session.flush()

    service = ExportService(session, library=library, storage_root=tmp_path / "storage")
    summary = service.export_project(project)
    assert summary.passed is False
    assert summary.docx_path is None
    assert any("not_approved" in w for w in summary.warnings)
