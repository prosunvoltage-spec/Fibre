"""Decide-Endpoint: startet Rule Engine für einen NVT."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SettingsDep
from app.classification.decision_builder import DecisionBuilder
from app.config import Settings
from app.core.repositories import NvtRepo
from app.ruleplans import RulePlanLibrary

router = APIRouter(prefix="/api/projects/{project_id}/nvts/{nvt_id}/decide", tags=["decide"])


class DecideOut(BaseModel):
    nvt_id: str
    status: str
    decision_code: str
    selected_ruleplan_id: str | None
    rule_confidence: float
    candidates: list[str] = []
    warnings: list[str] = []
    reasons: list[str] = []


@router.post("", response_model=DecideOut)
def decide_nvt(
    project_id: UUID,
    nvt_id: UUID,
    force: bool = Query(default=False),
    user: str | None = Query(default=None),
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> DecideOut:
    nvt = NvtRepo(db).get(nvt_id)
    if nvt is None or nvt.project_id != project_id:
        raise HTTPException(status_code=404, detail="NVT nicht gefunden")

    library = RulePlanLibrary(settings.knowledge_path / "regelplaene").load()
    builder = DecisionBuilder(
        db,
        library=library,
        user=user,
        ruleset_version=settings.current_ruleset_version,
        critical_completeness_threshold=float(settings.rule_critical_completeness),
        auto_approve_rule_conf=float(settings.rule_auto_approve_rule_conf),
        auto_approve_completeness=float(settings.rule_auto_approve_completeness),
        tie_threshold=float(settings.rule_tie_threshold),
    )
    outcome = builder.decide_for_nvt(nvt, force=force)

    return DecideOut(
        nvt_id=outcome.nvt_id,
        status=outcome.status.value,
        decision_code=outcome.decision_code.value,
        selected_ruleplan_id=outcome.selected_ruleplan_id,
        rule_confidence=outcome.rule_confidence,
        candidates=outcome.candidates,
        warnings=outcome.warnings,
        reasons=outcome.reasons,
    )
