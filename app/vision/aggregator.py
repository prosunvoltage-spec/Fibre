"""Multi-Foto-Aggregation, falls Provider nur Einzelfoto-Antworten liefert.

Der Default-Weg ist Single-Call-Multi-Image; der Aggregator ist der
Fallback und die Konfliktprüfung.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.enums import NvtPosition, RoadClass, Ternary
from app.vision.schema import VisionEnvironmentResponse

# Ternary-Felder, die durch konservative Regel aggregiert werden
_TERNARY_FIELDS = (
    "road_present", "sidewalk_present", "cycleway_present",
    "shared_cycle_footway_present", "parking_lane_present",
    "seiten_streifen_present", "private_property", "business_property",
    "driveway_present", "intersection_present", "junction_present",
    "cul_de_sac", "curve_present", "bus_stop_nearby", "fire_access",
    "parked_vehicles_in_workarea", "sight_relations_affected",
)


def _agg_ternary(values: list[Ternary]) -> tuple[Ternary, str | None]:
    """Widersprüche → UNKNOWN + contradiction-Note.

    - Nur ``UNKNOWN`` → ``UNKNOWN``
    - Nur ``YES`` (+ evt. UNKNOWN) → ``YES``
    - Nur ``NO`` (+ evt. UNKNOWN) → ``NO``
    - Mischung ``YES`` und ``NO`` → ``UNKNOWN`` + contradiction
    """
    non_unknown = {v for v in values if v != Ternary.UNKNOWN}
    if not non_unknown:
        return Ternary.UNKNOWN, None
    if len(non_unknown) == 1:
        return next(iter(non_unknown)), None
    return Ternary.UNKNOWN, "yes/no-Widerspruch zwischen Fotos"


def _agg_enum(values: list[str], default: str) -> tuple[str, str | None]:
    non_unknown = {v for v in values if v != default}
    if not non_unknown:
        return default, None
    if len(non_unknown) == 1:
        return next(iter(non_unknown)), None
    return default, f"Widerspruch zwischen Fotos: {sorted(non_unknown)}"


def _agg_number(values: list[Decimal | None]) -> Decimal | None:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return None
    # Konservativ: Median, aber nur wenn alle innerhalb 15 % Abweichung
    lo, hi = min(non_null), max(non_null)
    if hi > 0 and (hi - lo) / hi > Decimal("0.15"):
        return None
    return sum(non_null) / Decimal(len(non_null))


def aggregate_multi_photo(
    per_photo: list[VisionEnvironmentResponse],
) -> VisionEnvironmentResponse:
    """Verschmelzt mehrere Vision-Antworten (pro Foto) zu einem Ergebnis."""
    if not per_photo:
        return VisionEnvironmentResponse(manual_review_suggested=True)
    if len(per_photo) == 1:
        return per_photo[0]

    data: dict[str, Any] = {}
    contradictions: list[str] = []

    # Ternary-Aggregation
    for field in _TERNARY_FIELDS:
        values = [Ternary(getattr(p, field)) for p in per_photo]
        agg, note = _agg_ternary(values)
        data[field] = agg
        if note:
            contradictions.append(f"{field}: {note}")

    # Enums
    positions = [str(NvtPosition(p.nvt_position).value) for p in per_photo]
    pos, note = _agg_enum(positions, "unknown")
    data["nvt_position"] = NvtPosition(pos)
    if note:
        contradictions.append(f"nvt_position: {note}")

    classes = [str(RoadClass(p.road_class).value) for p in per_photo]
    cls, note = _agg_enum(classes, "unknown")
    data["road_class"] = RoadClass(cls)
    if note:
        contradictions.append(f"road_class: {note}")

    # Zahlen
    for numfield in (
        "sidewalk_width_m", "roadway_width_m", "cycleway_width_m",
        "distance_nvt_to_road_m",
    ):
        data[numfield] = _agg_number([getattr(p, numfield) for p in per_photo])

    # Listen: mergen + deduplizieren
    for listfield in ("existing_signs", "existing_barriers", "obstacles", "uncertainties"):
        merged: list[str] = []
        for p in per_photo:
            for item in getattr(p, listfield):
                if item not in merged:
                    merged.append(item)
        data[listfield] = merged

    # Contradictions aggregieren (eigene + neue)
    for p in per_photo:
        for c in p.contradictions:
            if c not in contradictions:
                contradictions.append(c)
    data["contradictions"] = contradictions

    # Meta
    data["vision_confidence"] = min(p.vision_confidence for p in per_photo)
    data["manual_review_suggested"] = (
        any(p.manual_review_suggested for p in per_photo) or len(contradictions) > 0
    )

    # per_photo_notes zusammenführen
    notes: dict[str, str] = {}
    for p in per_photo:
        notes.update(p.per_photo_notes)
    data["per_photo_notes"] = notes

    return VisionEnvironmentResponse(**data)
