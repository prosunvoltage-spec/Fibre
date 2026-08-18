"""Deterministische Rule Engine.

Reine Funktionen — kein I/O, keine Netzwerkaufrufe, keine DB.
Kann komplett per Unit-Test abgedeckt werden.
"""

from app.rules.engine import (
    RuleEngineOutcome,
    RulePlanCandidateResult,
    decide,
)

__all__ = ["RuleEngineOutcome", "RulePlanCandidateResult", "decide"]
