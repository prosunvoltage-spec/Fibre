"""Persistiert Rule-Engine-Ergebnisse als Decision + RulePlanCandidate."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import DecisionCode, NvtStatus
from app.core.models import Decision, Nvt, RulePlanCandidate
from app.core.repositories import AuditRepo, NvtRepo
from app.core.schemas import (
    EnvironmentAnalysisSchema,
    WorkAreaSchema,
)
from app.ruleplans import RulePlanLibrary
from app.rules import RuleEngineOutcome, decide

logger = logging.getLogger(__name__)


@dataclass
class DecideOutcome:
    nvt_id: str
    status: NvtStatus
    decision_code: DecisionCode
    selected_ruleplan_id: str | None
    rule_confidence: float
    candidates: list[str] = field(default_factory=list)  # ruleplan_ids in rank order
    warnings: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class DecisionBuilder:
    """Führt die Rule Engine für einen NVT aus und schreibt das Ergebnis in die DB."""

    def __init__(
        self,
        session: Session,
        library: RulePlanLibrary,
        *,
        user: str | None = None,
        ruleset_version: str = "v1",
        critical_completeness_threshold: float = 0.5,
        auto_approve_rule_conf: float = 0.9,
        auto_approve_completeness: float = 0.9,
        tie_threshold: float = 0.05,
    ) -> None:
        self.session = session
        self.library = library
        self.user = user
        self.ruleset_version = ruleset_version
        self.critical = critical_completeness_threshold
        self.auto_conf = auto_approve_rule_conf
        self.auto_comp = auto_approve_completeness
        self.tie = tie_threshold
        self._nvt_repo = NvtRepo(session)
        self._audit = AuditRepo(session)

    def decide_for_nvt(self, nvt: Nvt, *, force: bool = False) -> DecideOutcome:
        # EnvironmentAnalysis muss existieren
        if nvt.environment is None:
            return DecideOutcome(
                nvt_id=str(nvt.id),
                status=NvtStatus(nvt.status),
                decision_code=DecisionCode.NICHT_BEURTEILBAR,
                selected_ruleplan_id=None,
                rule_confidence=0.0,
                warnings=["Keine EnvironmentAnalysis vorhanden — Vision zuerst ausführen"],
            )

        if nvt.decision is not None and not force:
            return DecideOutcome(
                nvt_id=str(nvt.id),
                status=NvtStatus(nvt.status),
                decision_code=DecisionCode(nvt.decision.code),
                selected_ruleplan_id=nvt.decision.selected_ruleplan_id,
                rule_confidence=float(nvt.decision.rule_confidence),
                warnings=["Decision existiert bereits — force=true zum Überschreiben"],
            )

        env_schema = self._env_to_schema(nvt.environment)
        wa_schema = self._workarea_to_schema(nvt.work_area) if nvt.work_area else None

        outcome: RuleEngineOutcome = decide(
            env=env_schema,
            ruleplans=self.library.all(),
            work_area=wa_schema,
            critical_completeness_threshold=self._d(self.critical),
            auto_approve_rule_conf=self._d(self.auto_conf),
            auto_approve_completeness=self._d(self.auto_comp),
            tie_threshold=self._d(self.tie),
        )

        # Alte Kandidaten + Decision entfernen
        if nvt.decision is not None:
            self.session.delete(nvt.decision)
        for c in list(nvt.ruleplan_candidates):
            self.session.delete(c)
        self.session.flush()

        # Kandidaten schreiben (bidirektional, damit nvt.ruleplan_candidates sofort gefüllt ist)
        for cand in outcome.candidates:
            row = RulePlanCandidate(
                nvt_id=nvt.id,
                ruleplan_id=cand.ruleplan_id,
                matched_predicates=list(cand.matched_predicates),
                unmet_requirements=list(cand.unmet_requirements),
                triggered_exclusions=list(cand.triggered_exclusions),
                score=cand.score,
                rank=cand.rank,
                trace=list(cand.trace),
            )
            nvt.ruleplan_candidates.append(row)
            self.session.add(row)

        # Decision schreiben
        decision = Decision(
            nvt_id=nvt.id,
            selected_ruleplan_id=outcome.selected_ruleplan_id,
            code=outcome.code,
            vision_confidence=outcome.vision_confidence,
            rule_confidence=outcome.rule_confidence,
            data_completeness=outcome.data_completeness,
            human_review_required=outcome.human_review_required,
            reasons=list(outcome.reasons),
            warnings=list(outcome.warnings),
            ruleset_version=self.ruleset_version,
            ruleplan_revision_hash=outcome.ruleplan_revision_hash,
            model_id=nvt.environment.model_id or "",
            prompt_hash=nvt.environment.prompt_hash or "",
            trace_json=outcome.trace,
            created_at=datetime.now(UTC),
        )
        nvt.decision = decision
        self.session.add(decision)
        self.session.flush()

        # Statuswechsel
        current = NvtStatus(nvt.status) if isinstance(nvt.status, str) else nvt.status
        # Nach ANALYZED: sinnvoll NEEDS_REVIEW (Human erforderlich)
        target = NvtStatus.NEEDS_REVIEW
        if outcome.code == DecisionCode.PRIVATFLAECHE:
            # Auch Privatfläche braucht menschliche Bestätigung — kein automatisches APPROVED
            target = NvtStatus.NEEDS_REVIEW
        if current != target:
            try:
                self._nvt_repo.update_status(nvt, target)
            except Exception as exc:
                logger.warning("Statuswechsel %s→%s: %s", current, target, exc)

        self._audit.append(
            action="RULE_ENGINE_DECIDED",
            user=self.user,
            project_id=nvt.project_id,
            nvt_id=nvt.id,
            new_value=outcome.selected_ruleplan_id,
            payload={
                "code": outcome.code.value,
                "rule_confidence": float(outcome.rule_confidence),
                "candidates": [c.ruleplan_id for c in outcome.candidates[:5]],
                "warnings": outcome.warnings,
            },
        )

        return DecideOutcome(
            nvt_id=str(nvt.id),
            status=NvtStatus(nvt.status),
            decision_code=outcome.code,
            selected_ruleplan_id=outcome.selected_ruleplan_id,
            rule_confidence=float(outcome.rule_confidence),
            candidates=[c.ruleplan_id for c in outcome.candidates],
            warnings=outcome.warnings,
            reasons=outcome.reasons,
        )

    # ------------------------------------------------------------------
    # Umwandlung ORM → Pydantic-Schema
    # ------------------------------------------------------------------

    def _env_to_schema(self, env) -> EnvironmentAnalysisSchema:  # type: ignore[no-untyped-def]
        return EnvironmentAnalysisSchema(
            nvt_id=env.nvt_id,
            road_present=env.road_present,
            sidewalk_present=env.sidewalk_present,
            cycleway_present=env.cycleway_present,
            shared_cycle_footway_present=env.shared_cycle_footway_present,
            parking_lane_present=env.parking_lane_present,
            seiten_streifen_present=env.seiten_streifen_present,
            private_property=env.private_property,
            business_property=env.business_property,
            driveway_present=env.driveway_present,
            intersection_present=env.intersection_present,
            junction_present=env.junction_present,
            cul_de_sac=env.cul_de_sac,
            curve_present=env.curve_present,
            bus_stop_nearby=env.bus_stop_nearby,
            fire_access=env.fire_access,
            nvt_position=env.nvt_position,
            road_class=env.road_class,
            sidewalk_width_m=env.sidewalk_width_m,
            roadway_width_m=env.roadway_width_m,
            cycleway_width_m=env.cycleway_width_m,
            distance_nvt_to_road_m=env.distance_nvt_to_road_m,
            parked_vehicles_in_workarea=env.parked_vehicles_in_workarea,
            existing_signs=list(env.existing_signs or []),
            existing_barriers=list(env.existing_barriers or []),
            obstacles=list(env.obstacles or []),
            sight_relations_affected=env.sight_relations_affected,
            contributing_photos=[str(p) for p in (env.contributing_photos or [])],
            vision_confidence=env.vision_confidence,
            data_completeness=env.data_completeness,
            contradictions=list(env.contradictions or []),
            raw_provider_output=dict(env.raw_provider_output or {}),
            model_id=env.model_id or "",
            model_version=env.model_version,
            prompt_hash=env.prompt_hash or "",
            created_at=env.created_at,
        )

    def _workarea_to_schema(self, wa) -> WorkAreaSchema:  # type: ignore[no-untyped-def]
        return WorkAreaSchema(
            nvt_id=wa.nvt_id,
            bulli_length_m=wa.bulli_length_m,
            bulli_width_m=wa.bulli_width_m,
            required_traffic_area=wa.required_traffic_area,
            affects_sidewalk=wa.affects_sidewalk,
            affects_road=wa.affects_road,
            affects_cycleway=wa.affects_cycleway,
            affects_driveway=wa.affects_driveway,
            affects_bus_stop=wa.affects_bus_stop,
            remaining_roadway_width_m=wa.remaining_roadway_width_m,
            remaining_sidewalk_width_m=wa.remaining_sidewalk_width_m,
            edited_by_user=wa.edited_by_user,
            edited_at=wa.edited_at,
        )

    @staticmethod
    def _d(v: float) -> "Decimal":
        from decimal import Decimal

        return Decimal(str(v))
