"""Benannte Prädikate über EnvironmentAnalysis + optional WorkArea.

Alle Prädikate haben Ternary-Semantik: sie geben ``Ternary.YES/NO/UNKNOWN``
zurück, damit die Rule Engine ``UNKNOWN`` als Grund für
``MANUELLE_PRÜFUNG_ERFORDERLICH`` behandeln kann.

Boolesche Prädikate (Endpunkte, wo UNKNOWN als False zählen darf) heißen
``*_bool`` und sind aus einem Ternary-Prädikat abgeleitet.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

from app.core.enums import (
    NvtPosition,
    RoadClass,
    Ternary,
)
from app.core.schemas import EnvironmentAnalysisSchema, WorkAreaSchema

# ---------------------------------------------------------------------------
# Basis-Hilfsfunktionen
# ---------------------------------------------------------------------------


def _t(v: Ternary | str) -> Ternary:
    """Normalisiert Str/Enum auf Ternary."""
    return Ternary(v) if isinstance(v, str) else v


def _ternary_and(a: Ternary, b: Ternary) -> Ternary:
    """Konservatives AND: UNKNOWN dominiert wenn Ergebnis unklar."""
    if a == Ternary.NO or b == Ternary.NO:
        return Ternary.NO
    if a == Ternary.UNKNOWN or b == Ternary.UNKNOWN:
        return Ternary.UNKNOWN
    return Ternary.YES


def _ternary_or(a: Ternary, b: Ternary) -> Ternary:
    if a == Ternary.YES or b == Ternary.YES:
        return Ternary.YES
    if a == Ternary.UNKNOWN or b == Ternary.UNKNOWN:
        return Ternary.UNKNOWN
    return Ternary.NO


def _ternary_not(v: Ternary) -> Ternary:
    if v == Ternary.UNKNOWN:
        return Ternary.UNKNOWN
    return Ternary.NO if v == Ternary.YES else Ternary.YES


# ---------------------------------------------------------------------------
# Verkehrsraum-Prädikate (aus EnvironmentAnalysis)
# ---------------------------------------------------------------------------


def has_road(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.road_present)


def has_sidewalk(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.sidewalk_present)


def has_cycleway(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.cycleway_present)


def has_shared_cycle_footway(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.shared_cycle_footway_present)


def has_parking_lane(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.parking_lane_present)


def is_private_property(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.private_property)


def is_business_property(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.business_property)


def is_driveway_present(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.driveway_present)


def is_intersection_area(env: EnvironmentAnalysisSchema) -> Ternary:
    return _ternary_or(_t(env.intersection_present), _t(env.junction_present))


def is_cul_de_sac(env: EnvironmentAnalysisSchema) -> Ternary:
    """Sackgasse — entweder direkt erkannt oder aus Straßenklasse."""
    if RoadClass(env.road_class) == RoadClass.SACKGASSE:
        return Ternary.YES
    return _t(env.cul_de_sac)


def is_curve(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.curve_present)


def bus_stop_nearby(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.bus_stop_nearby)


def has_fire_access(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.fire_access)


def is_residential_street(env: EnvironmentAnalysisSchema) -> Ternary:
    cls = RoadClass(env.road_class)
    if cls == RoadClass.WOHNSTRASSE:
        return Ternary.YES
    if cls == RoadClass.UNKNOWN:
        return Ternary.UNKNOWN
    return Ternary.NO


def is_main_road(env: EnvironmentAnalysisSchema) -> Ternary:
    cls = RoadClass(env.road_class)
    if cls == RoadClass.HAUPTVERKEHR:
        return Ternary.YES
    if cls == RoadClass.UNKNOWN:
        return Ternary.UNKNOWN
    return Ternary.NO


def is_operating_area(env: EnvironmentAnalysisSchema) -> Ternary:
    """Betriebsweg (Stadtwerke-Gelände o.ä.)."""
    cls = RoadClass(env.road_class)
    if cls == RoadClass.BETRIEBSWEG:
        return Ternary.YES
    pos = NvtPosition(env.nvt_position)
    if pos == NvtPosition.ON_BUSINESS_PREMISES:
        return Ternary.YES
    return _t(env.business_property)


def sight_relations_ok(env: EnvironmentAnalysisSchema) -> Ternary:
    return _ternary_not(_t(env.sight_relations_affected))


def parked_vehicles_in_workarea(env: EnvironmentAnalysisSchema) -> Ternary:
    return _t(env.parked_vehicles_in_workarea)


# ---------------------------------------------------------------------------
# Prädikate, die WorkArea berücksichtigen
# ---------------------------------------------------------------------------


def road_affected(
    env: EnvironmentAnalysisSchema, wa: WorkAreaSchema | None
) -> Ternary:
    """Betrifft der Arbeitsbereich die Fahrbahn?"""
    if wa is not None:
        return Ternary.YES if wa.affects_road else Ternary.NO
    # Ableitung aus NVT-Position + Vorhandensein
    if _t(env.road_present) == Ternary.NO:
        return Ternary.NO
    pos = NvtPosition(env.nvt_position)
    if pos == NvtPosition.AT_ROADSIDE:
        return Ternary.YES
    if pos in (NvtPosition.ON_PRIVATE_PROPERTY, NvtPosition.ON_BUSINESS_PREMISES):
        return Ternary.NO
    return Ternary.UNKNOWN


def sidewalk_affected(
    env: EnvironmentAnalysisSchema, wa: WorkAreaSchema | None
) -> Ternary:
    if wa is not None:
        return Ternary.YES if wa.affects_sidewalk else Ternary.NO
    if _t(env.sidewalk_present) == Ternary.NO:
        return Ternary.NO
    pos = NvtPosition(env.nvt_position)
    if pos in (NvtPosition.ON_SIDEWALK, NvtPosition.BEHIND_SIDEWALK):
        return Ternary.YES
    return Ternary.UNKNOWN


def cycleway_affected(
    env: EnvironmentAnalysisSchema, wa: WorkAreaSchema | None
) -> Ternary:
    if wa is not None:
        return Ternary.YES if wa.affects_cycleway else Ternary.NO
    if _t(env.cycleway_present) == Ternary.NO:
        return Ternary.NO
    return Ternary.UNKNOWN


def driveway_affected(
    env: EnvironmentAnalysisSchema, wa: WorkAreaSchema | None
) -> Ternary:
    if wa is not None:
        return Ternary.YES if wa.affects_driveway else Ternary.NO
    return _t(env.driveway_present)


def bus_stop_affected(
    env: EnvironmentAnalysisSchema, wa: WorkAreaSchema | None
) -> Ternary:
    if wa is not None:
        return Ternary.YES if wa.affects_bus_stop else Ternary.NO
    return _t(env.bus_stop_nearby)


# ---------------------------------------------------------------------------
# Zahlen-Prädikate (Restbreiten, Abstände)
# ---------------------------------------------------------------------------


def remaining_roadway_ge(
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None,
    min_m: float | Decimal,
) -> Ternary:
    """Restfahrbahnbreite ≥ min_m? (Standard-Auflage Münster: 3,00 m)."""
    threshold = Decimal(str(min_m))
    if wa is not None and wa.remaining_roadway_width_m is not None:
        return Ternary.YES if wa.remaining_roadway_width_m >= threshold else Ternary.NO
    if env.roadway_width_m is not None:
        # Konservativ: ohne WorkArea nur wenn Fahrbahn nachweislich breit genug
        return (
            Ternary.YES
            if env.roadway_width_m >= threshold + Decimal("1.5")
            else Ternary.UNKNOWN
        )
    return Ternary.UNKNOWN


def remaining_sidewalk_ge(
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None,
    min_m: float | Decimal,
) -> Ternary:
    threshold = Decimal(str(min_m))
    if wa is not None and wa.remaining_sidewalk_width_m is not None:
        return (
            Ternary.YES if wa.remaining_sidewalk_width_m >= threshold else Ternary.NO
        )
    if env.sidewalk_width_m is not None:
        return (
            Ternary.YES
            if env.sidewalk_width_m >= threshold + Decimal("0.6")
            else Ternary.UNKNOWN
        )
    return Ternary.UNKNOWN


# ---------------------------------------------------------------------------
# Prädikat-Registry für Rule Engine
# ---------------------------------------------------------------------------

PredicateFn = Callable[..., Ternary]

# Namen entsprechen ``machine_predicate``-Werten in ``metadata.json``.
PREDICATE_REGISTRY: dict[str, PredicateFn] = {
    # Verkehrsraum
    "has_road": has_road,
    "has_sidewalk": has_sidewalk,
    "has_cycleway": has_cycleway,
    "has_shared_cycle_footway": has_shared_cycle_footway,
    "has_parking_lane": has_parking_lane,
    "is_private_property": is_private_property,
    "is_business_property": is_business_property,
    "is_driveway_present": is_driveway_present,
    "is_intersection_area": is_intersection_area,
    "is_cul_de_sac": is_cul_de_sac,
    "is_curve": is_curve,
    "bus_stop_nearby": bus_stop_nearby,
    "has_fire_access": has_fire_access,
    "is_residential_street": is_residential_street,
    "is_main_road": is_main_road,
    "is_operating_area": is_operating_area,
    "sight_relations_ok": sight_relations_ok,
    "parked_vehicles_in_workarea": parked_vehicles_in_workarea,
    # WorkArea-abhängig
    "road_affected": road_affected,
    "sidewalk_affected": sidewalk_affected,
    "cycleway_affected": cycleway_affected,
    "driveway_affected": driveway_affected,
    "bus_stop_affected": bus_stop_affected,
    # Zahlen
    "remaining_roadway_ge": remaining_roadway_ge,
    "remaining_sidewalk_ge": remaining_sidewalk_ge,
}


class UnknownPredicate(KeyError):
    """Wird in metadata.json ein ``machine_predicate`` genannt, das nicht existiert."""


def evaluate_predicate(
    name: str,
    env: EnvironmentAnalysisSchema,
    wa: WorkAreaSchema | None = None,
    args: dict | None = None,
) -> Ternary:
    """Ruft ein registriertes Prädikat auf.

    ``args`` sind zusätzliche Keyword-Argumente aus metadata.json (z.B.
    ``{"min_m": 3.0}`` für ``remaining_roadway_ge``).
    """
    if name not in PREDICATE_REGISTRY:
        raise UnknownPredicate(
            f"machine_predicate '{name}' nicht in PREDICATE_REGISTRY"
        )
    fn = PREDICATE_REGISTRY[name]
    kwargs: dict = dict(args or {})
    # WorkArea-abhängige Prädikate nehmen (env, wa[, ...])
    wa_required = {
        "road_affected",
        "sidewalk_affected",
        "cycleway_affected",
        "driveway_affected",
        "bus_stop_affected",
        "remaining_roadway_ge",
        "remaining_sidewalk_ge",
    }
    if name in wa_required:
        return fn(env, wa, **kwargs) if kwargs else fn(env, wa)
    return fn(env, **kwargs) if kwargs else fn(env)
