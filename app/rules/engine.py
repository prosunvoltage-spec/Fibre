"""Deterministische Rule Engine — reine Funktion, kein I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.enums import DecisionCode
from app.core.schemas import EnvironmentAnalysisSchema, WorkAreaSchema
from app.ruleplans.loader import RulePlanEntry
from app.rules.candidate_search import find_candidates
from app.rules.exclusions import check_hard_exclusions
from app.rules.ranking import RankedCandidate, is_tie, rank


@dataclass
class RulePlanCandidateResult:
    """Was in der DB als RulePlanCandidate-Row landet."""

    ruleplan_id: str
    matched_predicates: list[str]
    unmet_requirements: list[str]
    triggered_exclusions: list[str]
    score: Decimal
    rank: int
    trace: list[str]
    is_complete: bool


@dataclass
class RuleEngineOutcome:
    """Ergebnis von :func:`decide`. Wird vom DecisionBuilder persistiert."""

    code: DecisionCode
    selected_ruleplan_id: str | None
    ruleplan_revision_hash: str | None
    candidates: list[RulePlanCandidateResult]
    vision_confidence: Decimal
    rule_confidence: Decimal
    data_completeness: Decimal
    human_review_required: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: dict = field(default_factory=dict)


def _collect_warnings(env: EnvironmentAnalysisSchema | None) -> list[str]:
    warnings: list[str] = []
    if env is None:
        return warnings
    from app.core.enums import Ternary

    if Ternary(env.intersection_present) == Ternary.YES:
        warnings.append("Kreuzung im Nahbereich — Sichtdreiecke prüfen")
    if Ternary(env.junction_present) == Ternary.YES:
        warnings.append("Einmündung im Nahbereich — Sichtdreiecke prüfen")
    if Ternary(env.cul_de_sac) == Ternary.YES:
        warnings.append("Sackgasse — Vollsperrung / Anwohner-Absprache prüfen")
    if Ternary(env.bus_stop_nearby) == Ternary.YES:
        warnings.append("Bushaltestelle betroffen — Stadtwerke Münster informieren")
    if Ternary(env.fire_access) == Ternary.YES:
        warnings.append("Feuerwehrzufahrt — jederzeit befahrbar halten")
    if Ternary(env.sight_relations_affected) == Ternary.YES:
        warnings.append("Sichtbeziehungen beeinträchtigt")
    if Ternary(env.parked_vehicles_in_workarea) == Ternary.YES:
        warnings.append("Parkende Fahrzeuge im Arbeitsbereich — Haltverbot ausreichend?")
    return warnings


def _rule_confidence(
    top: RankedCandidate,
    tie: bool,
    warnings: list[str],
    env: EnvironmentAnalysisSchema,
) -> Decimal:
    """Konservativer Rule-Confidence-Wert in [0, 1]."""
    conf = top.score
    if tie:
        conf -= Decimal("0.2")
    if warnings:
        conf -= Decimal("0.05") * Decimal(len(warnings))
    if top.result.unmet_requirements:
        conf -= Decimal("0.1")
    if not top.result.entry.schema.is_complete:
        conf = min(conf, Decimal("0.5"))  # unvollständige Metadaten deckeln
    return max(Decimal("0"), min(conf, Decimal("1")))


def _to_candidate_result(rc: RankedCandidate) -> RulePlanCandidateResult:
    return RulePlanCandidateResult(
        ruleplan_id=rc.result.entry.schema.id,
        matched_predicates=list(rc.result.matched_predicates),
        unmet_requirements=list(rc.result.unmet_requirements),
        triggered_exclusions=list(rc.result.triggered_exclusions),
        score=rc.score,
        rank=rc.rank,
        trace=list(rc.result.trace),
        is_complete=rc.result.entry.schema.is_complete,
    )


def decide(
    env: EnvironmentAnalysisSchema | None,
    ruleplans: list[RulePlanEntry],
    work_area: WorkAreaSchema | None = None,
    *,
    critical_completeness_threshold: Decimal = Decimal("0.5"),
    auto_approve_rule_conf: Decimal = Decimal("0.9"),
    auto_approve_completeness: Decimal = Decimal("0.9"),
    tie_threshold: Decimal = Decimal("0.05"),
) -> RuleEngineOutcome:
    """Kernfunktion: aus Umgebung + Bibliothek einen Regelplan-Vorschlag ableiten."""

    warnings = _collect_warnings(env)

    hard = check_hard_exclusions(
        env=env,
        wa=work_area,
        critical_completeness_threshold=critical_completeness_threshold,
        ruleplan_library_empty=(len(ruleplans) == 0),
    )
    if hard is not None:
        return RuleEngineOutcome(
            code=hard.code,
            selected_ruleplan_id=None,
            ruleplan_revision_hash=None,
            candidates=[],
            vision_confidence=(env.vision_confidence if env else Decimal("0")),
            rule_confidence=Decimal("0"),
            data_completeness=(env.data_completeness if env else Decimal("0")),
            human_review_required=True,
            reasons=[hard.reason],
            warnings=warnings,
            trace={"hard_exclusion": hard.reason},
        )

    assert env is not None  # nach check_hard_exclusions

    match_results = find_candidates(ruleplans, env, work_area)
    all_candidates = match_results
    surviving = [
        c for c in match_results if c.matched and not c.triggered_exclusions
    ]

    if not surviving:
        # Wenn niemand matched → REGELPLAN_NICHT_GEFUNDEN
        return RuleEngineOutcome(
            code=DecisionCode.REGELPLAN_NICHT_GEFUNDEN,
            selected_ruleplan_id=None,
            ruleplan_revision_hash=None,
            candidates=[
                _to_candidate_result(rc)
                for rc in rank(all_candidates)
            ],
            vision_confidence=env.vision_confidence,
            rule_confidence=Decimal("0"),
            data_completeness=env.data_completeness,
            human_review_required=True,
            reasons=[
                "Kein Regelplan passt zur erfassten Situation "
                "(Regelplan-Metadaten evtl. unvollständig)"
            ],
            warnings=warnings,
            trace={"total_candidates": len(all_candidates), "surviving": 0},
        )

    ranked = rank(surviving)
    tie = is_tie(ranked, tie_threshold)

    top = ranked[0]
    rule_confidence = _rule_confidence(top, tie, warnings, env)

    # Entscheidungscode
    if tie:
        code = DecisionCode.WIDERSPRUCH
        selected: str | None = None
        reasons = [
            f"Top-2 Kandidaten liegen zu dicht beieinander: "
            f"{ranked[0].result.entry.schema.id}={ranked[0].score:.2f} vs. "
            f"{ranked[1].result.entry.schema.id}={ranked[1].score:.2f}"
        ]
        human_review = True
        revision_hash = None
    else:
        selected = top.result.entry.schema.id
        revision_hash = top.result.entry.schema.revision_hash
        reasons = [
            f"Bester Kandidat: {selected} (Score {top.score:.2f}, "
            f"{len(top.result.matched_predicates)} Prädikate erfüllt)"
        ]

        # Freigabecodes
        if (
            not top.result.unmet_requirements
            and top.result.entry.schema.is_complete
            and env.data_completeness >= auto_approve_completeness
            and rule_confidence >= auto_approve_rule_conf
            and not warnings
        ):
            code = DecisionCode.AUTO_FREIGABE_VORBEREITET
            human_review = True  # trotzdem Human-in-the-Loop; siehe REVIEW_PROCESS.md §1
        else:
            code = DecisionCode.AUTO_VORSCHLAG
            human_review = True

    # Alle geprüften Kandidaten für Trace mit aufführen
    all_ranked = rank(all_candidates)
    candidate_results = [_to_candidate_result(rc) for rc in all_ranked]

    return RuleEngineOutcome(
        code=code,
        selected_ruleplan_id=selected,
        ruleplan_revision_hash=revision_hash,
        candidates=candidate_results,
        vision_confidence=env.vision_confidence,
        rule_confidence=rule_confidence,
        data_completeness=env.data_completeness,
        human_review_required=human_review,
        reasons=reasons,
        warnings=warnings,
        trace={
            "total_candidates": len(all_candidates),
            "surviving": len(surviving),
            "top_score": str(top.score),
            "tie": tie,
        },
    )
