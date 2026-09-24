"""QA-Prüfliste vor dem Word-Export (siehe REVIEW_PROCESS.md §7)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import DecisionCode, NvtStatus, PhotoKind, ReviewAction
from app.core.models import Nvt, Project
from app.ruleplans import RulePlanLibrary


@dataclass
class QaGateFailure:
    nvt_id: str | None
    nvt_number: str | None
    check: str
    message: str


@dataclass
class QaGateReport:
    project_id: str
    passed: bool
    checks_run: int
    failures: list[QaGateFailure] = field(default_factory=list)

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    def to_json(self) -> dict:
        return {
            "project_id": self.project_id,
            "passed": self.passed,
            "checks_run": self.checks_run,
            "failure_count": self.failure_count,
            "failures": [f.__dict__ for f in self.failures],
        }


def _photo_kinds_present(nvt: Nvt) -> set[str]:
    kinds = set()
    for p in nvt.photos:
        kinds.add(p.kind.value if hasattr(p.kind, "value") else str(p.kind))
    return kinds


def _has_approved_review(nvt: Nvt) -> bool:
    for r in nvt.reviews:
        action = r.action.value if hasattr(r.action, "value") else str(r.action)
        if action == ReviewAction.APPROVED.value:
            return True
    return False


def run_qa_gate(
    project: Project,
    nvts: list[Nvt],
    ruleplan_library: RulePlanLibrary,
    *,
    require_review: bool = True,
) -> QaGateReport:
    """Führt alle Prüfungen aus REVIEW_PROCESS.md §7 durch.

    ``require_review=True`` (Default) verlangt mindestens einen
    ``APPROVED``-Review pro NVT. Für Tests/Vorschauen kann das ausgeschaltet
    werden — im echten Export-Endpoint immer True.
    """
    checks = 0
    failures: list[QaGateFailure] = []
    seen_numbers: dict[str, str] = {}

    for nvt in nvts:
        nvt_number = nvt.nvt_number
        nvt_id_str = str(nvt.id)

        # 1. NVT-Nummer vorhanden + eindeutig
        checks += 1
        if not nvt_number:
            failures.append(QaGateFailure(nvt_id_str, nvt_number, "nvt_number", "leer"))
        else:
            if nvt_number in seen_numbers:
                failures.append(
                    QaGateFailure(
                        nvt_id_str, nvt_number, "duplicate",
                        f"NVT-Nummer bereits vergeben (auch {seen_numbers[nvt_number]})",
                    )
                )
            seen_numbers[nvt_number] = nvt_id_str

        # 2. Mindestens ein Foto
        checks += 1
        if not nvt.photos:
            failures.append(QaGateFailure(nvt_id_str, nvt_number, "no_photo", "Kein Foto"))

        # 3. Adresse ODER GPS
        checks += 1
        has_address = bool(nvt.address_json and any(v for v in nvt.address_json.values() if v))
        has_gps = bool(
            nvt.location_json
            and nvt.location_json.get("latitude") is not None
            and nvt.location_json.get("longitude") is not None
        )
        if not (has_address or has_gps):
            failures.append(
                QaGateFailure(nvt_id_str, nvt_number, "no_location", "Weder Adresse noch GPS")
            )

        # 4. EnvironmentAnalysis vorhanden
        checks += 1
        if nvt.environment is None:
            failures.append(
                QaGateFailure(nvt_id_str, nvt_number, "no_environment", "Vision noch nicht gelaufen")
            )

        # 5. Decision vorhanden mit Regelplan ODER PRIVATFLAECHE
        checks += 1
        if nvt.decision is None:
            failures.append(
                QaGateFailure(nvt_id_str, nvt_number, "no_decision", "Rule Engine noch nicht gelaufen")
            )
        else:
            code = nvt.decision.code.value if hasattr(nvt.decision.code, "value") else str(nvt.decision.code)
            if code == DecisionCode.PRIVATFLAECHE.value:
                pass  # ok — Sonderpfad ohne Regelplan
            elif nvt.decision.selected_ruleplan_id is None:
                failures.append(
                    QaGateFailure(
                        nvt_id_str, nvt_number, "no_ruleplan",
                        f"Kein Regelplan gewählt (code={code})",
                    )
                )
            else:
                # Regelplan muss in Bibliothek existieren
                entry = ruleplan_library.get(nvt.decision.selected_ruleplan_id)
                if entry is None:
                    failures.append(
                        QaGateFailure(
                            nvt_id_str, nvt_number, "ruleplan_missing_in_library",
                            f"Regelplan {nvt.decision.selected_ruleplan_id} nicht in /knowledge/regelplaene/",
                        )
                    )

        # 6. Freigabe (APPROVED-Review) — nur wenn require_review=True
        if require_review:
            checks += 1
            if not _has_approved_review(nvt):
                failures.append(
                    QaGateFailure(
                        nvt_id_str, nvt_number, "not_approved",
                        f"Kein APPROVED-Review vorhanden (status={nvt.status})",
                    )
                )

        # 7. Status ≥ APPROVED
        if require_review:
            checks += 1
            status = NvtStatus(nvt.status)
            if status not in (NvtStatus.APPROVED, NvtStatus.EXPORTED):
                failures.append(
                    QaGateFailure(
                        nvt_id_str, nvt_number, "wrong_status",
                        f"Status {status.value}, erwartet APPROVED oder EXPORTED",
                    )
                )

        # 8. Visualisierung vorhanden bei nicht-Privatfläche
        checks += 1
        needs_viz = True
        if nvt.decision is not None:
            code_val = nvt.decision.code.value if hasattr(nvt.decision.code, "value") else str(nvt.decision.code)
            if code_val == DecisionCode.PRIVATFLAECHE.value:
                needs_viz = False
        if needs_viz and nvt.visualization is None:
            failures.append(
                QaGateFailure(
                    nvt_id_str, nvt_number, "no_visualization",
                    "Absicherungs-Darstellung fehlt (nicht Privatfläche)",
                )
            )

    passed = len(failures) == 0
    return QaGateReport(
        project_id=str(project.id),
        passed=passed,
        checks_run=checks,
        failures=failures,
    )
