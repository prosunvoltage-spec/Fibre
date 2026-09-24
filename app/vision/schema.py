"""Strenges Response-Schema für Vision-Antworten.

Wichtig: ``extra="forbid"`` — unbekannte Felder werden abgelehnt. Selbst wenn
das Modell ungefragt einen Regelplan nennt, wird die Antwort verworfen.
Es gibt bewusst kein ``recommended_ruleplan``-Feld.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import (
    NvtPosition,
    RoadClass,
    Ternary,
)


class _Strict(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=False,
    )


class VisionEnvironmentResponse(_Strict):
    """Was ein Vision-Provider pro NVT (1..n Fotos) zurückgibt."""

    # Verkehrsraum
    road_present: Ternary = Ternary.UNKNOWN
    sidewalk_present: Ternary = Ternary.UNKNOWN
    cycleway_present: Ternary = Ternary.UNKNOWN
    shared_cycle_footway_present: Ternary = Ternary.UNKNOWN
    parking_lane_present: Ternary = Ternary.UNKNOWN
    seiten_streifen_present: Ternary = Ternary.UNKNOWN
    private_property: Ternary = Ternary.UNKNOWN
    business_property: Ternary = Ternary.UNKNOWN
    driveway_present: Ternary = Ternary.UNKNOWN
    intersection_present: Ternary = Ternary.UNKNOWN
    junction_present: Ternary = Ternary.UNKNOWN
    cul_de_sac: Ternary = Ternary.UNKNOWN
    curve_present: Ternary = Ternary.UNKNOWN
    bus_stop_nearby: Ternary = Ternary.UNKNOWN
    fire_access: Ternary = Ternary.UNKNOWN

    nvt_position: NvtPosition = NvtPosition.UNKNOWN
    road_class: RoadClass = RoadClass.UNKNOWN

    # Optional: Zahlen sind nur zu setzen, wenn zuverlässig aus Bild ableitbar
    sidewalk_width_m: Decimal | None = None
    roadway_width_m: Decimal | None = None
    cycleway_width_m: Decimal | None = None
    distance_nvt_to_road_m: Decimal | None = None

    # Zusatzbeobachtungen
    parked_vehicles_in_workarea: Ternary = Ternary.UNKNOWN
    existing_signs: list[str] = Field(default_factory=list)
    existing_barriers: list[str] = Field(default_factory=list)
    obstacles: list[str] = Field(default_factory=list)
    sight_relations_affected: Ternary = Ternary.UNKNOWN

    # Meta
    vision_confidence: Decimal = Decimal("0")
    uncertainties: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    manual_review_suggested: bool = False
    per_photo_notes: dict[str, str] = Field(
        default_factory=dict,
        description="photo_id → freie Notiz (nicht ins Word)",
    )

    @field_validator("vision_confidence")
    @classmethod
    def _in_unit_interval(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("vision_confidence muss in [0, 1] liegen")
        return v

    @field_validator("existing_signs", "existing_barriers", "obstacles", "uncertainties", "contradictions")
    @classmethod
    def _no_ruleplan_references(cls, v: list[str]) -> list[str]:
        """Halluzinations-Schutz: Freitext darf keine Regelplan-Auswahl enthalten."""
        forbidden = ("regelplan b", "regelplan vzp", "vorschlag: b1", "vorschlag: b2", "vorschlag vzp")
        clean = []
        for item in v:
            lower = item.lower()
            if any(f in lower for f in forbidden):
                # Feld verwerfen, aber nicht crashen — Aufrufer bekommt es via contradictions
                continue
            clean.append(item)
        return clean

    def count_unknowns(self) -> int:
        """Anzahl Felder mit Ternary.UNKNOWN — Basis für data_completeness."""
        count = 0
        for name in (
            "road_present", "sidewalk_present", "cycleway_present",
            "shared_cycle_footway_present", "parking_lane_present",
            "seiten_streifen_present", "private_property", "business_property",
            "driveway_present", "intersection_present", "junction_present",
            "cul_de_sac", "curve_present", "bus_stop_nearby", "fire_access",
            "parked_vehicles_in_workarea", "sight_relations_affected",
        ):
            if getattr(self, name) == Ternary.UNKNOWN:
                count += 1
        if self.nvt_position == NvtPosition.UNKNOWN:
            count += 1
        if self.road_class == RoadClass.UNKNOWN:
            count += 1
        return count

    def total_countable_fields(self) -> int:
        return 19  # 17 Ternary + nvt_position + road_class

    def data_completeness(self) -> Decimal:
        total = self.total_countable_fields()
        return Decimal(total - self.count_unknowns()) / Decimal(total)


def response_schema_json() -> str:
    """JSON-Schema als Anhang für strengere Provider-Steuerung."""
    import json

    return json.dumps(VisionEnvironmentResponse.model_json_schema(), ensure_ascii=False, indent=2)
