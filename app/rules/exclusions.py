"""Sofort-Ausschlüsse, die vor der Kandidatensuche greifen.

Nach RULE_ENGINE.md §6 haben diese Vorrang vor jeder anderen Logik.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.enums import DecisionCode, NvtPosition, Ternary
from app.core.schemas import EnvironmentAnalysisSchema, WorkAreaSchema


class HardExclusion:
    """Container für einen Sofort-Ausschluss.

    Wenn `code` gesetzt ist, wird die Pipeline beendet und der Code zurückgegeben.
    """

    def __init__(self, code: DecisionCode, reason: str) -> None:
        self.code = code
        self.reason = reason


def check_hard_exclusions(
    env: EnvironmentAnalysisSchema | None,
    wa: WorkAreaSchema | None,
    critical_completeness_threshold: Decimal,
    ruleplan_library_empty: bool = False,
) -> HardExclusion | None:
    """Prüft die harten No-Gos in der Reihenfolge aus RULE_ENGINE.md §6."""

    if env is None:
        return HardExclusion(
            DecisionCode.NICHT_BEURTEILBAR,
            "Keine EnvironmentAnalysis vorhanden — Vision noch nicht gelaufen",
        )

    # 1. Privatfläche → keine öffentliche VRA notwendig
    if Ternary(env.private_property) == Ternary.YES:
        return HardExclusion(
            DecisionCode.PRIVATFLAECHE,
            "Privatfläche — keine öffentliche verkehrsrechtliche Anordnung erforderlich",
        )

    # 2. Betriebsgelände + Arbeitsbereich innerhalb
    if Ternary(env.business_property) == Ternary.YES:
        pos = NvtPosition(env.nvt_position)
        if pos == NvtPosition.ON_BUSINESS_PREMISES or (
            wa is not None and wa.required_traffic_area.value == "private_area"
        ):
            return HardExclusion(
                DecisionCode.PRIVATFLAECHE,
                "Betriebsgelände — keine öffentliche VRA erforderlich",
            )

    # 3. Regelplan-Bibliothek leer
    if ruleplan_library_empty:
        return HardExclusion(
            DecisionCode.REGELPLAN_NICHT_GEFUNDEN,
            "Regelplan-Bibliothek ist leer — keine Auswahl möglich",
        )

    # 4. Datenlage unzureichend
    if env.data_completeness < critical_completeness_threshold:
        return HardExclusion(
            DecisionCode.MANUELLE_PRUEFUNG,
            f"Datenvollständigkeit {env.data_completeness:.0%} < "
            f"Schwelle {critical_completeness_threshold:.0%}",
        )

    # 5. Widersprüche zwischen Fotos wurden von Vision gemeldet
    if env.contradictions:
        return HardExclusion(
            DecisionCode.MANUELLE_PRUEFUNG,
            f"Widersprüche zwischen Fotos: {len(env.contradictions)} Einträge",
        )

    return None
