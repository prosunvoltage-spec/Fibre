"""Orchestriert den Export: QA-Gate → Word + HTML → Export-Row in DB."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import NvtStatus
from app.core.models import Export, Nvt, Project
from app.core.repositories import AuditRepo, NvtRepo
from app.documents.html_report import build_html_report
from app.documents.word_builder import build_word_anlage
from app.ruleplans import RulePlanLibrary
from app.validation import QaGateReport, run_qa_gate

logger = logging.getLogger(__name__)


@dataclass
class ExportSummary:
    project_id: str
    docx_path: str | None
    html_report_path: str | None
    qa_report: dict
    included_nvt_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    superseded_export_ids: list[str] = field(default_factory=list)
    passed: bool = False


class ExportService:
    def __init__(
        self,
        session: Session,
        library: RulePlanLibrary,
        *,
        storage_root: Path,
        user: str | None = None,
    ) -> None:
        self.session = session
        self.library = library
        self.storage_root = storage_root
        self.user = user
        self._nvt_repo = NvtRepo(session)
        self._audit = AuditRepo(session)

    def export_project(
        self, project: Project, *, require_review: bool = True, dry_run: bool = False,
        editable_overlay: bool = False,
    ) -> ExportSummary:
        nvts = self._nvt_repo.list_for_project(project.id)

        qa_report: QaGateReport = run_qa_gate(
            project, nvts, self.library, require_review=require_review,
        )

        if not qa_report.passed:
            self._audit.append(
                action="QA_GATE_FAILED",
                user=self.user,
                project_id=project.id,
                new_value=str(qa_report.failure_count),
                payload=qa_report.to_json(),
            )
            return ExportSummary(
                project_id=str(project.id),
                docx_path=None,
                html_report_path=None,
                qa_report=qa_report.to_json(),
                passed=False,
                warnings=[f"{f.check}: {f.message}" for f in qa_report.failures],
            )

        self._audit.append(
            action="QA_GATE_PASSED",
            user=self.user,
            project_id=project.id,
            payload={"checks_run": qa_report.checks_run},
        )

        if dry_run:
            return ExportSummary(
                project_id=str(project.id),
                docx_path=None,
                html_report_path=None,
                qa_report=qa_report.to_json(),
                passed=True,
                included_nvt_ids=[str(n.id) for n in nvts],
                warnings=["dry_run: keine Dateien geschrieben"],
            )

        # Vorherige Exports als superseded markieren
        superseded: list[str] = []
        for old in self.session.scalars(
            select(Export).where(Export.project_id == project.id, Export.superseded.is_(False))
        ):
            old.superseded = True
            superseded.append(str(old.id))
        self.session.flush()

        # Ausgabepfade
        out_dir = self.storage_root / "projects" / str(project.id) / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        version = self.session.scalar(
            select(Export).where(Export.project_id == project.id)
        )
        version_count = (
            self.session.query(Export).filter(Export.project_id == project.id).count() + 1
        )
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        docx_path = out_dir / f"VRA_NVT_Gesamt_{date_str}_v{version_count}.docx"
        html_path = out_dir / f"analysis_report_{date_str}_v{version_count}.html"

        word_result = build_word_anlage(
            project, nvts, self.library, docx_path, editable_overlay=editable_overlay
        )
        build_html_report(project, nvts, self._audit, html_path)

        # Export-Row schreiben
        export = Export(
            project_id=project.id,
            docx_path=str(docx_path),
            pdf_path=None,
            included_nvt_ids=[str(n.id) for n in nvts],
            qa_gate_report=qa_report.to_json(),
            generated_by=self.user or "system",
            generated_at=datetime.now(UTC),
            superseded=False,
        )
        self.session.add(export)
        self.session.flush()

        # Statuswechsel APPROVED → EXPORTED
        exported: list[str] = []
        for nvt in nvts:
            current = NvtStatus(nvt.status)
            if current == NvtStatus.APPROVED:
                try:
                    self._nvt_repo.update_status(nvt, NvtStatus.EXPORTED)
                    exported.append(str(nvt.id))
                except Exception as exc:
                    logger.warning("Statuswechsel APPROVED→EXPORTED: %s", exc)

        self._audit.append(
            action="EXPORT_COMPLETED",
            user=self.user,
            project_id=project.id,
            new_value=str(docx_path),
            payload={
                "export_id": str(export.id),
                "docx_path": str(docx_path),
                "html_path": str(html_path),
                "nvt_count": len(nvts),
                "exported_status_change": len(exported),
                "superseded": superseded,
            },
        )

        return ExportSummary(
            project_id=str(project.id),
            docx_path=str(docx_path),
            html_report_path=str(html_path),
            qa_report=qa_report.to_json(),
            passed=True,
            included_nvt_ids=[str(n.id) for n in nvts],
            warnings=word_result.warnings,
            superseded_export_ids=superseded,
        )
