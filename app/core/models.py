"""SQLAlchemy 2 ORM-Modelle.

Value-Objekte mit vielen Skalar-Feldern (Address, Location) werden als
JSON-Spalten in ``Nvt`` gespeichert. Analysen und Entscheidungen bekommen
eigene Tabellen mit 1:1-Relation, damit sie unabhängig versioniert und
zeitlich aufgereiht werden können.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enums import (
    DecisionCode,
    NvtPosition,
    NvtStatus,
    PhotoKind,
    RequiredTrafficArea,
    ReviewAction,
    RoadClass,
    Ternary,
    TrafficUser,
)
from app.core.types import GUID


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_label: Mapped[str | None] = mapped_column(String(200))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    client: Mapped[str | None] = mapped_column(String(200))
    contractor: Mapped[str] = mapped_column(String(200), nullable=False)
    site_manager_name: Mapped[str | None] = mapped_column(String(200))
    on_site_responsible_name: Mapped[str | None] = mapped_column(String(200))
    on_site_responsible_phone: Mapped[str | None] = mapped_column(String(50))
    ruleset_version: Mapped[str] = mapped_column(String(20), nullable=False)
    vision_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    nvts: Mapped[list[Nvt]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    exports: Mapped[list[Export]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# NVT — Aggregat
# ---------------------------------------------------------------------------


class Nvt(Base):
    __tablename__ = "nvts"
    __table_args__ = (UniqueConstraint("project_id", "nvt_number", name="uq_nvt_per_project"),)

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nvt_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[NvtStatus] = mapped_column(
        String(20), default=NvtStatus.NEW, nullable=False, index=True
    )

    # Value-Objects als JSON
    address_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    location_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list)

    duplicates_of: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("nvts.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    project: Mapped[Project] = relationship(back_populates="nvts")
    photos: Mapped[list[Photo]] = relationship(
        back_populates="nvt", cascade="all, delete-orphan"
    )
    environment: Mapped[EnvironmentAnalysis | None] = relationship(
        back_populates="nvt", cascade="all, delete-orphan", uselist=False
    )
    work_area: Mapped[WorkArea | None] = relationship(
        back_populates="nvt", cascade="all, delete-orphan", uselist=False
    )
    traffic_users: Mapped[list[TrafficUserAssessment]] = relationship(
        back_populates="nvt", cascade="all, delete-orphan"
    )
    ruleplan_candidates: Mapped[list[RulePlanCandidate]] = relationship(
        back_populates="nvt", cascade="all, delete-orphan"
    )
    decision: Mapped[Decision | None] = relationship(
        back_populates="nvt", cascade="all, delete-orphan", uselist=False
    )
    visualization: Mapped[Visualization | None] = relationship(
        back_populates="nvt", cascade="all, delete-orphan", uselist=False
    )
    reviews: Mapped[list[Review]] = relationship(
        back_populates="nvt", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Photo
# ---------------------------------------------------------------------------


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    nvt_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("nvts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    exif: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ocr_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    kind: Mapped[PhotoKind] = mapped_column(String(20), default=PhotoKind.ORIGINAL, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    nvt: Mapped[Nvt] = relationship(back_populates="photos")


# ---------------------------------------------------------------------------
# Environment Analysis
# ---------------------------------------------------------------------------


class EnvironmentAnalysis(Base):
    __tablename__ = "environment_analyses"

    nvt_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("nvts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Ternary-Felder als String
    road_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    sidewalk_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    cycleway_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    shared_cycle_footway_present: Mapped[Ternary] = mapped_column(
        String(10), default=Ternary.UNKNOWN
    )
    parking_lane_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    seiten_streifen_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    private_property: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    business_property: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    driveway_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    intersection_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    junction_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    cul_de_sac: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    curve_present: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    bus_stop_nearby: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    fire_access: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)

    nvt_position: Mapped[NvtPosition] = mapped_column(String(30), default=NvtPosition.UNKNOWN)
    road_class: Mapped[RoadClass] = mapped_column(String(20), default=RoadClass.UNKNOWN)

    sidewalk_width_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    roadway_width_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    cycleway_width_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    distance_nvt_to_road_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    parked_vehicles_in_workarea: Mapped[Ternary] = mapped_column(
        String(10), default=Ternary.UNKNOWN
    )
    existing_signs: Mapped[list[str]] = mapped_column(JSON, default=list)
    existing_barriers: Mapped[list[str]] = mapped_column(JSON, default=list)
    obstacles: Mapped[list[str]] = mapped_column(JSON, default=list)
    sight_relations_affected: Mapped[Ternary] = mapped_column(
        String(10), default=Ternary.UNKNOWN
    )

    contributing_photos: Mapped[list[str]] = mapped_column(JSON, default=list)
    vision_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))
    data_completeness: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))
    contradictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_provider_output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model_id: Mapped[str] = mapped_column(String(100), default="")
    model_version: Mapped[str | None] = mapped_column(String(50))
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    nvt: Mapped[Nvt] = relationship(back_populates="environment")


# ---------------------------------------------------------------------------
# Work Area
# ---------------------------------------------------------------------------


class WorkArea(Base):
    __tablename__ = "work_areas"

    nvt_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("nvts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    bulli_position: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    bulli_length_m: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("5.5"))
    bulli_width_m: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.0"))
    equipment_position: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    barrier_polygon: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    required_traffic_area: Mapped[RequiredTrafficArea] = mapped_column(
        String(40), default=RequiredTrafficArea.UNKNOWN
    )

    affects_sidewalk: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_road: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_cycleway: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_driveway: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_bus_stop: Mapped[bool] = mapped_column(Boolean, default=False)

    remaining_roadway_width_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    remaining_sidewalk_width_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    edited_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    nvt: Mapped[Nvt] = relationship(back_populates="work_area")


# ---------------------------------------------------------------------------
# Traffic User Assessment
# ---------------------------------------------------------------------------


class TrafficUserAssessment(Base):
    __tablename__ = "traffic_user_assessments"
    __table_args__ = (UniqueConstraint("nvt_id", "user", name="uq_traffic_user"),)

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    nvt_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("nvts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped[TrafficUser] = mapped_column(String(30), nullable=False)
    affected: Mapped[bool] = mapped_column(Boolean, default=False)
    current_route: Mapped[str | None] = mapped_column(Text)
    proposed_route: Mapped[str | None] = mapped_column(Text)
    safe: Mapped[Ternary] = mapped_column(String(10), default=Ternary.UNKNOWN)
    reason: Mapped[str | None] = mapped_column(Text)
    source_document: Mapped[str | None] = mapped_column(String(200))

    nvt: Mapped[Nvt] = relationship(back_populates="traffic_users")


# ---------------------------------------------------------------------------
# Rule Plan Candidate
# ---------------------------------------------------------------------------


class RulePlanCandidate(Base):
    __tablename__ = "ruleplan_candidates"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    nvt_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("nvts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ruleplan_id: Mapped[str] = mapped_column(String(20), nullable=False)
    matched_predicates: Mapped[list[str]] = mapped_column(JSON, default=list)
    unmet_requirements: Mapped[list[str]] = mapped_column(JSON, default=list)
    triggered_exclusions: Mapped[list[str]] = mapped_column(JSON, default=list)
    score: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))
    rank: Mapped[int] = mapped_column(Integer, default=0)
    trace: Mapped[list[str]] = mapped_column(JSON, default=list)

    nvt: Mapped[Nvt] = relationship(back_populates="ruleplan_candidates")


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class Decision(Base):
    __tablename__ = "decisions"

    nvt_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("nvts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    selected_ruleplan_id: Mapped[str | None] = mapped_column(String(20))
    code: Mapped[DecisionCode] = mapped_column(String(50), nullable=False)
    vision_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))
    rule_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))
    data_completeness: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    ruleset_version: Mapped[str] = mapped_column(String(20), nullable=False)
    ruleplan_revision_hash: Mapped[str | None] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(String(100), default="")
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    trace_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    nvt: Mapped[Nvt] = relationship(back_populates="decision")


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------


class Visualization(Base):
    __tablename__ = "visualizations"

    nvt_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("nvts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    base_photo_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("photos.id"), nullable=False)
    symbols: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    shapes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    rendered_photo_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("photos.id"))
    final_photo_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("photos.id"))
    edited_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    nvt: Mapped[Nvt] = relationship(back_populates="visualization")


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    nvt_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("nvts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[ReviewAction] = mapped_column(String(30), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    nvt: Mapped[Nvt] = relationship(back_populates="reviews")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    docx_path: Mapped[str] = mapped_column(String(500), nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    included_nvt_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    qa_gate_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    generated_by: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    superseded: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="exports")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    user: Mapped[str | None] = mapped_column(String(100))
    project_id: Mapped[UUID | None] = mapped_column(GUID(), index=True)
    nvt_id: Mapped[UUID | None] = mapped_column(GUID(), index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    ruleset_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
