"""Pydantic v2 DTOs für alle Fach-Entities.

Die Schemas sind die Verträge zwischen API, Services und der Persistenz.
Alle Schemas verwenden ``extra="forbid"`` — unbekannte Felder werden
abgelehnt. Damit sind sie sowohl gegen versehentliche Feld-Drift als auch
gegen halluzinierte KI-Zusatzfelder geschützt (siehe AI_PIPELINE.md §7).

Siehe ``docs/DATA_MODEL.md`` für die zugehörige fachliche Beschreibung.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import (
    AddressSource,
    DecisionCode,
    LocationSource,
    NvtPosition,
    NvtStatus,
    OverlaySymbolType,
    PhotoKind,
    RequiredTrafficArea,
    ReviewAction,
    RoadClass,
    Ternary,
    TrafficUser,
)

# ---------------------------------------------------------------------------
# Basis-Konfiguration für alle Schemas
# ---------------------------------------------------------------------------


class _Strict(BaseModel):
    """Gemeinsame Basisklasse mit strengen Defaults."""

    model_config = ConfigDict(
        extra="forbid",  # unbekannte Felder verboten (Anti-Halluzination)
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=False,
    )


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


class AddressSchema(_Strict):
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str = "DE"
    raw: str | None = None
    source: AddressSource | None = None


class LocationSchema(_Strict):
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    accuracy_meters: Decimal | None = None
    source: LocationSource | None = None
    geocoder_name: str | None = None
    geocoded_at: datetime | None = None

    @field_validator("latitude")
    @classmethod
    def _lat_range(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (Decimal("-90") <= v <= Decimal("90")):
            raise ValueError("latitude außerhalb [-90, 90]")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon_range(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (Decimal("-180") <= v <= Decimal("180")):
            raise ValueError("longitude außerhalb [-180, 180]")
        return v


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectCreate(_Strict):
    name: str = Field(min_length=1, max_length=200)
    location_label: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    client: str | None = None
    contractor: str = Field(min_length=1)
    site_manager_name: str | None = None
    on_site_responsible_name: str | None = None
    on_site_responsible_phone: str | None = None
    ruleset_version: str
    vision_provider: str


class ProjectSchema(ProjectCreate):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Photo
# ---------------------------------------------------------------------------


class PhotoCreate(_Strict):
    nvt_id: UUID
    filename: str
    stored_path: str
    mime_type: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    sha256: str = Field(min_length=64, max_length=64)
    exif: dict[str, Any] = Field(default_factory=dict)
    ocr_json: dict[str, Any] | None = None
    kind: PhotoKind = PhotoKind.ORIGINAL


class PhotoSchema(PhotoCreate):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime


# ---------------------------------------------------------------------------
# Environment Analysis
# ---------------------------------------------------------------------------


class EnvironmentAnalysisSchema(_Strict):
    nvt_id: UUID

    # Verkehrsraum (Ternary — nie geraten)
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

    # NVT-Lage & Straßenklasse
    nvt_position: NvtPosition = NvtPosition.UNKNOWN
    road_class: RoadClass = RoadClass.UNKNOWN

    # Breiten in Metern (None wenn nicht zuverlässig ermittelbar)
    sidewalk_width_m: Decimal | None = None
    roadway_width_m: Decimal | None = None
    cycleway_width_m: Decimal | None = None
    distance_nvt_to_road_m: Decimal | None = None

    # weitere Beobachtungen
    parked_vehicles_in_workarea: Ternary = Ternary.UNKNOWN
    existing_signs: list[str] = Field(default_factory=list)
    existing_barriers: list[str] = Field(default_factory=list)
    obstacles: list[str] = Field(default_factory=list)
    sight_relations_affected: Ternary = Ternary.UNKNOWN

    # Meta
    contributing_photos: list[UUID] = Field(default_factory=list)
    vision_confidence: Decimal = Decimal("0")
    data_completeness: Decimal = Decimal("0")
    contradictions: list[str] = Field(default_factory=list)
    raw_provider_output: dict[str, Any] = Field(default_factory=dict)
    model_id: str = ""
    model_version: str | None = None
    prompt_hash: str = ""
    created_at: datetime | None = None

    @field_validator("vision_confidence", "data_completeness")
    @classmethod
    def _in_unit_interval(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("Confidence-Wert muss in [0, 1] liegen")
        return v


# ---------------------------------------------------------------------------
# Work Area
# ---------------------------------------------------------------------------


class OverlayPointSchema(_Strict):
    x: Decimal
    y: Decimal

    @field_validator("x", "y")
    @classmethod
    def _in_unit_interval(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("Overlay-Koordinaten müssen in [0, 1] liegen")
        return v


class OverlayShapeSchema(_Strict):
    kind: Literal["rect", "polygon", "line"]
    points: list[OverlayPointSchema]
    rotation: Decimal = Decimal("0")

    @field_validator("points")
    @classmethod
    def _min_points(cls, v: list[OverlayPointSchema]) -> list[OverlayPointSchema]:
        if len(v) < 2:
            raise ValueError("Shape braucht mindestens 2 Punkte")
        return v


class WorkAreaSchema(_Strict):
    nvt_id: UUID

    bulli_position: OverlayShapeSchema | None = None
    bulli_length_m: Decimal = Decimal("5.5")
    bulli_width_m: Decimal = Decimal("2.0")
    equipment_position: OverlayShapeSchema | None = None

    barrier_polygon: list[OverlayPointSchema] = Field(default_factory=list)
    required_traffic_area: RequiredTrafficArea = RequiredTrafficArea.UNKNOWN

    affects_sidewalk: bool = False
    affects_road: bool = False
    affects_cycleway: bool = False
    affects_driveway: bool = False
    affects_bus_stop: bool = False

    remaining_roadway_width_m: Decimal | None = None
    remaining_sidewalk_width_m: Decimal | None = None

    edited_by_user: bool = False
    edited_at: datetime | None = None


# ---------------------------------------------------------------------------
# Traffic User
# ---------------------------------------------------------------------------


class TrafficUserAssessmentSchema(_Strict):
    nvt_id: UUID
    user: TrafficUser
    affected: bool = False
    current_route: str | None = None
    proposed_route: str | None = None
    safe: Ternary = Ternary.UNKNOWN
    reason: str | None = None
    source_document: str | None = None


# ---------------------------------------------------------------------------
# RulePlan (aus /knowledge/regelplaene/, nicht in DB)
# ---------------------------------------------------------------------------


class RequirementSchema(_Strict):
    condition: str
    machine_predicate: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    source_document: str
    source_reference: str
    source_page: int | None = None
    notes: str | None = None


class RulePlanSchema(_Strict):
    """Aus ``metadata.json`` unter ``/knowledge/regelplaene/{id}/``."""

    id: str
    name: str
    quelle: str
    version: str = ""
    beschreibung: str = ""

    plan_pdf_path: str
    preview_png_path: str

    verkehrsraum: list[str] = Field(default_factory=list)
    geeignet_fuer: list[dict[str, Any]] = Field(default_factory=list)
    voraussetzungen: list[RequirementSchema] = Field(default_factory=list)
    ausschlusskriterien: list[RequirementSchema] = Field(default_factory=list)

    fussverkehr: dict[str, Any] = Field(default_factory=dict)
    radverkehr: dict[str, Any] = Field(default_factory=dict)
    fahrverkehr: dict[str, Any] = Field(default_factory=dict)

    besondere_hinweise: list[str] = Field(default_factory=list)
    allowed_symbols: list[OverlaySymbolType] = Field(default_factory=list)

    revision_hash: str
    is_complete: bool = False


class RulePlanCandidateSchema(_Strict):
    ruleplan_id: str
    matched_predicates: list[str] = Field(default_factory=list)
    unmet_requirements: list[str] = Field(default_factory=list)
    triggered_exclusions: list[str] = Field(default_factory=list)
    score: Decimal = Decimal("0")
    rank: int = 0
    trace: list[str] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def _score_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("score muss in [0, 1] liegen")
        return v


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class DecisionSchema(_Strict):
    nvt_id: UUID
    selected_ruleplan_id: str | None = None
    code: DecisionCode
    vision_confidence: Decimal = Decimal("0")
    rule_confidence: Decimal = Decimal("0")
    data_completeness: Decimal = Decimal("0")
    human_review_required: bool = True
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ruleset_version: str
    ruleplan_revision_hash: str | None = None
    model_id: str = ""
    prompt_hash: str = ""
    trace_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @field_validator("vision_confidence", "rule_confidence", "data_completeness")
    @classmethod
    def _in_unit_interval(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("Confidence-Wert muss in [0, 1] liegen")
        return v


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------


class OverlaySymbolSchema(_Strict):
    type: OverlaySymbolType
    x: Decimal
    y: Decimal
    rotation: Decimal = Decimal("0")
    scale: Decimal = Decimal("1")
    label: str | None = None

    @field_validator("x", "y")
    @classmethod
    def _in_unit_interval(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("Overlay-Koordinaten müssen in [0, 1] liegen")
        return v


class VisualizationSchema(_Strict):
    nvt_id: UUID
    base_photo_id: UUID
    symbols: list[OverlaySymbolSchema] = Field(default_factory=list)
    shapes: list[OverlayShapeSchema] = Field(default_factory=list)
    rendered_photo_id: UUID | None = None
    final_photo_id: UUID | None = None
    edited_by_user: bool = False
    edited_at: datetime | None = None


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewCreate(_Strict):
    nvt_id: UUID
    reviewer: str = Field(min_length=1)
    action: ReviewAction
    comment: str | None = None
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)


class ReviewSchema(ReviewCreate):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ExportSchema(_Strict):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    docx_path: str
    pdf_path: str | None = None
    included_nvt_ids: list[UUID] = Field(default_factory=list)
    qa_gate_report: dict[str, Any] = Field(default_factory=dict)
    generated_by: str
    generated_at: datetime
    superseded: bool = False


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


class AuditLogSchema(_Strict):
    id: int | None = None
    timestamp: datetime
    user: str | None = None
    project_id: UUID | None = None
    nvt_id: UUID | None = None
    action: str = Field(min_length=1)
    old_value: str | None = None
    new_value: str | None = None
    ruleset_version: str
    model_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# NVT — Aggregat
# ---------------------------------------------------------------------------


class NvtCreate(_Strict):
    project_id: UUID
    nvt_number: str = Field(min_length=1, max_length=32)
    address: AddressSchema | None = None
    location: LocationSchema | None = None


class NvtSchema(NvtCreate):
    id: UUID = Field(default_factory=uuid4)
    status: NvtStatus = NvtStatus.NEW
    warnings: list[str] = Field(default_factory=list)
    duplicates_of: UUID | None = None
    created_at: datetime
    updated_at: datetime

    photos: list[PhotoSchema] = Field(default_factory=list)
    environment_analysis: EnvironmentAnalysisSchema | None = None
    work_area: WorkAreaSchema | None = None
    traffic_users: list[TrafficUserAssessmentSchema] = Field(default_factory=list)
    ruleplan_candidates: list[RulePlanCandidateSchema] = Field(default_factory=list)
    decision: DecisionSchema | None = None
    visualization: VisualizationSchema | None = None
    reviews: list[ReviewSchema] = Field(default_factory=list)
