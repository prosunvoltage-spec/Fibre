"""Vorschlag eines Overlays anhand von Environment + Regelplan.

Erzeugt bewusst konservativ: eine schmale rote Absperrfläche und zwei Leitbaken
links/rechts des NVT. Der Reviewer verschiebt die Symbole in der UI (Phase 7).

Halluzinations-Schutz: Es werden nur Symbole vorgeschlagen, die im gewählten
Regelplan (`allowed_symbols` in metadata.json) belegt sind. Ist die Liste leer
(Metadaten nicht gepflegt), fällt der Proposer auf ein Standard-Set zurück
und gibt eine Warnung.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.enums import NvtPosition, OverlaySymbolType, Ternary
from app.core.schemas import (
    EnvironmentAnalysisSchema,
    OverlayPointSchema,
    OverlayShapeSchema,
    OverlaySymbolSchema,
    VisualizationSchema,
)
from app.ruleplans.loader import RulePlanEntry

# Wenn Regelplan-Metadaten unvollständig sind, dieses Standardset erlauben
_FALLBACK_ALLOWED: set[OverlaySymbolType] = {
    OverlaySymbolType.LEITBAKE,
    OverlaySymbolType.WARNBAKE,
    OverlaySymbolType.ABSPERRSCHRANKE,
    OverlaySymbolType.HALTVERBOT,
    OverlaySymbolType.ARROW,
    OverlaySymbolType.TEXT,
}


@dataclass
class ProposalResult:
    visualization: VisualizationSchema | None
    warnings: list[str] = field(default_factory=list)
    reason: str | None = None  # falls kein Vorschlag möglich

    def has_proposal(self) -> bool:
        return self.visualization is not None


def _allowed_symbols(entry: RulePlanEntry | None) -> tuple[set[OverlaySymbolType], list[str]]:
    warnings: list[str] = []
    if entry is None:
        warnings.append("Kein Regelplan gewählt — Standardsymbol-Set")
        return _FALLBACK_ALLOWED, warnings
    allowed = {OverlaySymbolType(s) for s in entry.schema.allowed_symbols}
    if not allowed:
        warnings.append(
            f"allowed_symbols in Regelplan {entry.schema.id} leer — "
            "Standard-Set genutzt, Fachanwender bitte metadata.json pflegen"
        )
        return _FALLBACK_ALLOWED, warnings
    return allowed, warnings


def _dec(v: float) -> Decimal:
    return Decimal(str(v))


def _pt(x: float, y: float) -> OverlayPointSchema:
    return OverlayPointSchema(x=_dec(x), y=_dec(y))


def _bulli_footprint() -> OverlayShapeSchema:
    """Rechteck für die Bulli-Standfläche neben dem NVT."""
    return OverlayShapeSchema(
        kind="rect",
        points=[_pt(0.32, 0.55), _pt(0.62, 0.85)],
    )


def _barrier_polygon(pos: NvtPosition) -> OverlayShapeSchema:
    """Grober Absperrbereich, abhängig von der NVT-Lage."""
    if pos in (NvtPosition.AT_ROADSIDE, NvtPosition.IN_INTERSECTION_AREA):
        # Länglicher Bereich entlang der Fahrbahnkante
        return OverlayShapeSchema(
            kind="polygon",
            points=[
                _pt(0.25, 0.55), _pt(0.70, 0.55),
                _pt(0.70, 0.85), _pt(0.25, 0.85),
            ],
        )
    # Standard: kompakter Bereich um den NVT
    return OverlayShapeSchema(
        kind="polygon",
        points=[
            _pt(0.30, 0.60), _pt(0.65, 0.60),
            _pt(0.65, 0.82), _pt(0.30, 0.82),
        ],
    )


def _leitbake_pair(
    allowed: set[OverlaySymbolType],
) -> list[OverlaySymbolSchema]:
    """Zwei Leitbaken an den beiden Enden der Absperrfläche."""
    result: list[OverlaySymbolSchema] = []
    typ = OverlaySymbolType.LEITBAKE if OverlaySymbolType.LEITBAKE in allowed else None
    if typ is None:
        typ = OverlaySymbolType.WARNBAKE if OverlaySymbolType.WARNBAKE in allowed else None
    if typ is None:
        return result
    for x, y in [(0.27, 0.62), (0.68, 0.62)]:
        result.append(OverlaySymbolSchema(
            type=typ, x=_dec(x), y=_dec(y), rotation=_dec(0), scale=_dec(1),
        ))
    return result


def _halt_signs(
    allowed: set[OverlaySymbolType], env: EnvironmentAnalysisSchema
) -> list[OverlaySymbolSchema]:
    """Haltverbotszeichen, wenn Parkstreifen betroffen ist."""
    if Ternary(env.parked_vehicles_in_workarea) != Ternary.YES:
        return []
    if OverlaySymbolType.HALTVERBOT not in allowed:
        return []
    return [
        OverlaySymbolSchema(
            type=OverlaySymbolType.HALTVERBOT,
            x=_dec(0.20), y=_dec(0.40), rotation=_dec(0), scale=_dec(0.6),
        )
    ]


def _arrow_maybe(allowed: set[OverlaySymbolType]) -> list[OverlaySymbolSchema]:
    if OverlaySymbolType.ARROW not in allowed:
        return []
    return [
        OverlaySymbolSchema(
            type=OverlaySymbolType.ARROW, x=_dec(0.48), y=_dec(0.75),
            rotation=_dec(0), scale=_dec(0.8),
        )
    ]


def propose_visualization(
    *,
    nvt_id,  # type: ignore[no-untyped-def]
    base_photo_id,  # type: ignore[no-untyped-def]
    env: EnvironmentAnalysisSchema,
    ruleplan: RulePlanEntry | None,
) -> ProposalResult:
    """Erzeugt einen initialen Overlay-Vorschlag."""
    if Ternary(env.private_property) == Ternary.YES:
        return ProposalResult(
            visualization=None,
            reason="Privatfläche — keine öffentliche Absicherung nötig",
        )

    allowed, warnings = _allowed_symbols(ruleplan)

    symbols: list[OverlaySymbolSchema] = []
    symbols.extend(_leitbake_pair(allowed))
    symbols.extend(_halt_signs(allowed, env))
    symbols.extend(_arrow_maybe(allowed))

    if not symbols:
        warnings.append(
            "Kein Symbol aus allowed_symbols verwendbar — Overlay bleibt leer"
        )

    if ruleplan is not None:
        symbols.append(
            OverlaySymbolSchema(
                type=OverlaySymbolType.TEXT,
                x=_dec(0.5), y=_dec(0.08),
                label=f"Regelplan: {ruleplan.schema.id}",
            )
        )

    shapes: list[OverlayShapeSchema] = [
        _bulli_footprint(),
        _barrier_polygon(NvtPosition(env.nvt_position)),
    ]

    viz = VisualizationSchema(
        nvt_id=nvt_id,
        base_photo_id=base_photo_id,
        symbols=symbols,
        shapes=shapes,
        rendered_photo_id=None,
        final_photo_id=None,
        edited_by_user=False,
        edited_at=None,
    )
    return ProposalResult(visualization=viz, warnings=warnings)
