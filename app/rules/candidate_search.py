"""Kandidatensuche über die Regelplan-Bibliothek.

Ein Regelplan gilt als **Kandidat**, wenn alle ``geeignet_fuer``-Bedingungen
aus seiner ``metadata.json`` als ``Ternary.YES`` bewertet werden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.enums import Ternary
from app.core.schemas import EnvironmentAnalysisSchema, WorkAreaSchema
from app.rules.predicates import UnknownPredicate, evaluate_predicate
from app.ruleplans.loader import RulePlanEntry


@dataclass
class CandidateMatchResult:
    """Zwischenergebnis der Kandidatensuche für einen einzelnen Regelplan."""

    entry: RulePlanEntry
    matched: bool
    matched_predicates: list[str] = field(default_factory=list)
    failed_predicates: list[str] = field(default_factory=list)
    unknown_predicates: list[str] = field(default_factory=list)
    unmet_requirements: list[str] = field(default_factory=list)
    triggered_exclusions: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


def _bool_from_ternary(value: Ternary, expected: bool | str) -> tuple[Ternary, str]:
    """Vergleicht Prädikat-Ergebnis mit erwartetem Wert aus metadata.json.

    Erwartete Werte: ``true``/``false`` (bool) oder ``"yes"``/``"no"``/``"unknown"``.
    Rückgabe: (result, note) — result ist YES bei Match, NO bei Widerspruch,
    UNKNOWN wenn Prädikat UNKNOWN liefert.
    """
    if isinstance(expected, bool):
        target = Ternary.YES if expected else Ternary.NO
    else:
        target = Ternary(str(expected).lower())

    if value == Ternary.UNKNOWN:
        return Ternary.UNKNOWN, f"Prädikat unklar (erwartet {target.value})"
    return (Ternary.YES if value == target else Ternary.NO), (
        f"Prädikat {value.value} == erwartet {target.value}"
    )


def _rule_line(rule: dict[str, Any]) -> str:
    parts = []
    if pred := rule.get("predicate") or rule.get("machine_predicate"):
        parts.append(pred)
    if "value" in rule:
        parts.append(f"= {rule['value']}")
    if args := rule.get("args"):
        parts.append(f"args={args}")
    return " ".join(parts) or repr(rule)


def _evaluate_geeignet_fuer(
    entry: RulePlanEntry,
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None,
    result: CandidateMatchResult,
) -> bool:
    """Alle Bedingungen aus ``geeignet_fuer`` müssen YES sein."""
    all_ok = True
    for i, rule in enumerate(entry.schema.geeignet_fuer):
        pred_name = rule.get("predicate") or rule.get("machine_predicate")
        if not pred_name:
            result.trace.append(f"geeignet_fuer[{i}]: kein Prädikatsname — übersprungen")
            all_ok = False
            continue
        try:
            value = evaluate_predicate(
                pred_name, env, wa=wa, args=rule.get("args")
            )
        except UnknownPredicate as exc:
            result.trace.append(f"geeignet_fuer[{i}]: {exc}")
            result.failed_predicates.append(pred_name)
            all_ok = False
            continue

        expected = rule.get("value", True)
        outcome, note = _bool_from_ternary(value, expected)
        line = f"geeignet_fuer[{i}] {_rule_line(rule)} → {note}"
        result.trace.append(line)

        if outcome == Ternary.YES:
            result.matched_predicates.append(pred_name)
        elif outcome == Ternary.NO:
            result.failed_predicates.append(pred_name)
            all_ok = False
        else:  # UNKNOWN
            result.unknown_predicates.append(pred_name)
            all_ok = False
    return all_ok


def _evaluate_requirements(
    entry: RulePlanEntry,
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None,
    result: CandidateMatchResult,
) -> None:
    """Voraussetzungen prüfen — nicht erfüllt heißt: noch kein Auto-Vorschlag."""
    for req in entry.schema.voraussetzungen:
        pred_name = req.machine_predicate
        if not pred_name:
            # Nur menschenlesbar, keine automatische Prüfung möglich
            result.unmet_requirements.append(
                f"{req.condition} (keine automatische Prüfung — {req.source_document})"
            )
            continue
        try:
            value = evaluate_predicate(pred_name, env, wa=wa, args=req.args)
        except UnknownPredicate:
            result.unmet_requirements.append(
                f"{req.condition} (Prädikat {pred_name} nicht implementiert)"
            )
            continue
        if value != Ternary.YES:
            result.unmet_requirements.append(
                f"{req.condition} → Prädikat {pred_name}={value.value}"
            )


def _evaluate_exclusions(
    entry: RulePlanEntry,
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None,
    result: CandidateMatchResult,
) -> None:
    """Ausschluss-Kriterien: bei YES fliegt der Kandidat raus."""
    for excl in entry.schema.ausschlusskriterien:
        pred_name = excl.machine_predicate
        if not pred_name:
            # Nur menschenlesbar — Reviewer muss selber prüfen
            continue
        try:
            value = evaluate_predicate(pred_name, env, wa=wa, args=excl.args)
        except UnknownPredicate:
            continue
        if value == Ternary.YES:
            result.triggered_exclusions.append(
                f"{excl.condition} → Prädikat {pred_name}=yes"
            )


def find_candidates(
    ruleplans: list[RulePlanEntry],
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None,
) -> list[CandidateMatchResult]:
    """Alle Regelpläne durchgehen und Kandidaten-Ergebnisse zurückgeben.

    Auch Nicht-Kandidaten werden im Ergebnis vertreten (mit ``matched=False``),
    damit die Rule Engine sie für den Trace verwenden kann.
    """
    results: list[CandidateMatchResult] = []
    for entry in ruleplans:
        r = CandidateMatchResult(entry=entry, matched=False)
        # Ohne geeignet_fuer-Regeln kann der Loader den Regelplan nicht prüfen
        if not entry.schema.geeignet_fuer:
            r.trace.append("Kein 'geeignet_fuer' definiert — Regelplan-Metadaten unvollständig")
            results.append(r)
            continue

        r.matched = _evaluate_geeignet_fuer(entry, env, wa, r)
        # Requirements + Exclusions immer prüfen (für Trace, auch wenn nicht matched)
        _evaluate_requirements(entry, env, wa, r)
        _evaluate_exclusions(entry, env, wa, r)
        results.append(r)
    return results
