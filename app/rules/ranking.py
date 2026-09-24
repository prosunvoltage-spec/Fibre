"""Ranking der überlebenden Regelplan-Kandidaten.

Score-Berechnung, Sortierung, Tiebreak-Erkennung.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.rules.candidate_search import CandidateMatchResult


@dataclass
class RankedCandidate:
    result: CandidateMatchResult
    score: Decimal
    rank: int


def _score(cand: CandidateMatchResult) -> Decimal:
    """Score in [0, 1] pro Regelplan.

    Faktoren:
      - Anteil erfüllter geeignet_fuer-Prädikate (dominant)
      - Anteil erfüllter Voraussetzungen
      - Bonus wenn ausschlusskriterien-frei
      - Bonus wenn Regelplan-Metadaten komplett (is_complete=True)
    """
    total_geeignet = len(cand.entry.schema.geeignet_fuer) or 1
    matched_ratio = Decimal(len(cand.matched_predicates)) / Decimal(total_geeignet)

    total_req = len(cand.entry.schema.voraussetzungen) or 1
    met_req = total_req - len(cand.unmet_requirements)
    req_ratio = Decimal(max(met_req, 0)) / Decimal(total_req)

    excl_bonus = Decimal("0") if cand.triggered_exclusions else Decimal("0.1")
    complete_bonus = Decimal("0.1") if cand.entry.schema.is_complete else Decimal("0")

    score = (
        Decimal("0.55") * matched_ratio
        + Decimal("0.25") * req_ratio
        + excl_bonus
        + complete_bonus
    )
    # In [0, 1] halten (Bonusse können knapp drüber gehen)
    return max(Decimal("0"), min(score, Decimal("1")))


def rank(candidates: list[CandidateMatchResult]) -> list[RankedCandidate]:
    """Sortiert absteigend nach Score (Tiebreak: alphabetisch nach ruleplan_id)."""
    scored = [(_score(c), c) for c in candidates]
    scored.sort(key=lambda t: (-t[0], t[1].entry.schema.id))
    return [
        RankedCandidate(result=c, score=s, rank=i + 1) for i, (s, c) in enumerate(scored)
    ]


def is_tie(ranked: list[RankedCandidate], threshold: Decimal) -> bool:
    """True, wenn Top-1 und Top-2 zu dicht beieinander liegen."""
    if len(ranked) < 2:
        return False
    return (ranked[0].score - ranked[1].score) < threshold
