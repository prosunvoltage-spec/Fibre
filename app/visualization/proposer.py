"""Vorschlag eines Overlays anhand von Environment + Regelplan.

Absperr-Algorithmus (abgeleitet aus den Referenz-VRA Roxel, Seiten 3–52 —
u.a. NVT 7101, 7103, 7104, 7115, 7116, 7117; siehe docs/REFERENCE_CASES.md)
------------------------------------------------------------------------
Die vom Fachanwender freigegebenen Referenzbilder folgen durchgehend
demselben Muster. Dieses Muster ist hier deterministisch nachgebaut:

1. **Die Absperrung ist eine offene rote Polylinie, keine gefüllte Fläche.**
   Gezeichnet wird die *Kante* der Absperrung entlang des Bodens, nicht der
   gesperrte Bereich selbst. In keinem Referenzfall ist eine Fläche
   eingefärbt.
2. **Die Polylinie liegt in der Bodenebene** und folgt der Geometrie des
   Verkehrsraums (Gehwegkante, NVT-Ecke, Bordstein). Sie hat typischerweise
   3 Stützpunkte: vom Gebäude/der Hecke abgehend, entlang der Arbeitsfläche,
   dann zur Fahrbahn hin abknickend. Dadurch wirkt sie räumlich, obwohl kein
   3D-Modell existiert.
3. **Leitbaken stehen an den Endpunkten der Polylinie**, nicht an Ecken einer
   gedachten Rechteckfläche. In den Referenzen sind es 2 Baken (bei
   Vollsperrung/Sackgasse mehr, s. NVT 7103), immer mit Bodenkontakt am
   jeweiligen Endpunkt.
4. **Der Bulli wird nicht als Objekt gezeichnet**, sondern als Textlabel
   „Standort Einblasbulli inkl. Einblasgerätschaft" innerhalb des
   abgesperrten Bereichs. Ein gezeichnetes Fahrzeug würde eine Genauigkeit
   suggerieren, die das Foto nicht hergibt.
5. **Der NVT selbst wird bei Bedarf per Textlabel markiert** („NVT <Nr>
   Standort", s. NVT 7115).

Die konkreten Bildkoordinaten sind bewusst grobe Startwerte, die der
Reviewer in der UI (Phase 7) verschiebt — sie sind ein Vorschlag, keine
Vermessung.

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

_BULLI_LABEL = "Standort Einblasbulli\ninkl. Einblasgerätschaft"


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


def _barrier_polyline(pos: NvtPosition) -> list[tuple[float, float]]:
    """Stützpunkte der Absperrkante in Bildkoordinaten (Regel 1–2 oben).

    Die Punkte liegen in der Bodenebene: kleineres y = weiter entfernt. Der
    Verlauf knickt zur Fahrbahn hin ab, wie in den Referenzfotos, statt ein
    achsparalleles Rechteck zu bilden.
    """
    if pos in (NvtPosition.AT_ROADSIDE, NvtPosition.IN_INTERSECTION_AREA):
        # NVT direkt an der Fahrbahnkante: Absperrung greift weiter in die
        # Fahrbahn aus (Referenz NVT 7101, 7116).
        return [(0.30, 0.52), (0.34, 0.66), (0.60, 0.70), (0.66, 0.62)]
    # Standard (NVT auf/hinter dem Gehweg): Absperrung bleibt im Gehwegbereich
    # und knickt am Ende zur Fahrbahn ab (Referenz NVT 7115, 7117).
    return [(0.33, 0.50), (0.35, 0.63), (0.57, 0.67), (0.62, 0.60)]


def _barrier_shape(pos: NvtPosition) -> OverlayShapeSchema:
    return OverlayShapeSchema(
        kind="line",
        points=[_pt(x, y) for x, y in _barrier_polyline(pos)],
    )


def _leitbaken_at_ends(
    allowed: set[OverlaySymbolType], polyline: list[tuple[float, float]]
) -> list[OverlaySymbolSchema]:
    """Leitbaken an den beiden Endpunkten der Absperrkante (Regel 3 oben)."""
    typ = OverlaySymbolType.LEITBAKE if OverlaySymbolType.LEITBAKE in allowed else None
    if typ is None:
        typ = OverlaySymbolType.WARNBAKE if OverlaySymbolType.WARNBAKE in allowed else None
    if typ is None:
        return []
    return [
        OverlaySymbolSchema(type=typ, x=_dec(x), y=_dec(y), rotation=_dec(0), scale=_dec(0.55))
        for x, y in (polyline[0], polyline[-1])
    ]


def _bulli_label(polyline: list[tuple[float, float]]) -> OverlaySymbolSchema:
    """Textlabel statt gezeichnetem Fahrzeug (Regel 4 oben), mittig im
    abgesperrten Bereich."""
    cx = sum(x for x, _ in polyline) / len(polyline)
    # Oberhalb des höchsten Polylinien-Punkts absetzen, damit das Label weder
    # die Absperrkante noch die Leitbaken an den Endpunkten überdeckt.
    cy = min(y for _, y in polyline) - 0.09
    return OverlaySymbolSchema(
        type=OverlaySymbolType.TEXT,
        x=_dec(round(cx, 3)), y=_dec(round(cy, 3)),
        label=_BULLI_LABEL,
        scale=_dec(0.7),
    )


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


def propose_visualization(
    *,
    nvt_id,  # type: ignore[no-untyped-def]
    base_photo_id,  # type: ignore[no-untyped-def]
    env: EnvironmentAnalysisSchema,
    ruleplan: RulePlanEntry | None,
) -> ProposalResult:
    """Erzeugt einen initialen Overlay-Vorschlag nach dem oben dokumentierten
    Absperr-Algorithmus."""
    if Ternary(env.private_property) == Ternary.YES:
        return ProposalResult(
            visualization=None,
            reason="Privatfläche — keine öffentliche Absicherung nötig",
        )

    allowed, warnings = _allowed_symbols(ruleplan)
    polyline = _barrier_polyline(NvtPosition(env.nvt_position))

    symbols: list[OverlaySymbolSchema] = []
    symbols.extend(_leitbaken_at_ends(allowed, polyline))
    symbols.extend(_halt_signs(allowed, env))

    if not symbols:
        warnings.append(
            "Kein Symbol aus allowed_symbols verwendbar — Overlay bleibt leer"
        )

    symbols.append(_bulli_label(polyline))

    if ruleplan is not None:
        symbols.append(
            OverlaySymbolSchema(
                type=OverlaySymbolType.TEXT,
                x=_dec(0.5), y=_dec(0.08),
                label=f"Regelplan: {ruleplan.schema.id}",
            )
        )

    shapes: list[OverlayShapeSchema] = [_barrier_shape(NvtPosition(env.nvt_position))]

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
