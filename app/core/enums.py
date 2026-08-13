"""Enums für Status, Entscheidungscodes und Prozess-Aktionen.

Diese Enums sind die maschinenlesbare Fassung dessen, was in
``docs/DATA_MODEL.md`` §1 und ``docs/REVIEW_PROCESS.md`` §2 beschrieben ist.
Reihenfolge und Werte sind fachlich bindend — Änderungen erfordern eine
Datenmigration.
"""

from __future__ import annotations

from enum import Enum


class NvtStatus(str, Enum):
    """Lebenszyklus eines einzelnen NVT-Falls."""

    NEW = "NEW"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPORTED = "EXPORTED"


class DecisionCode(str, Enum):
    """Ergebnis-Codes der Rule Engine (siehe RULE_ENGINE.md §2)."""

    AUTO_FREIGABE_VORBEREITET = "AUTO_FREIGABE_VORBEREITET"
    AUTO_VORSCHLAG = "AUTO_VORSCHLAG"
    MANUELLE_PRUEFUNG = "MANUELLE_PRUEFUNG_ERFORDERLICH"
    NICHT_BEURTEILBAR = "NICHT_BEURTEILBAR"
    REGELPLAN_NICHT_GEFUNDEN = "REGELPLAN_NICHT_GEFUNDEN"
    WIDERSPRUCH = "WIDERSPRUCH_ZWISCHEN_QUELLEN"
    PRIVATFLAECHE = "PRIVATFLAECHE_KEINE_OEFFENTLICHE_VRA"


class TrafficUser(str, Enum):
    """Verkehrsarten für die pro NVT eine Bewertung entsteht."""

    PEDESTRIAN = "pedestrians"
    CYCLIST = "cyclists"
    MOTOR_VEHICLE = "motor_vehicles"
    PUBLIC_TRANSPORT = "public_transport"
    EMERGENCY = "emergency_vehicles"
    RESIDENTIAL_ACCESS = "residential_access"


class Ternary(str, Enum):
    """Dreiwertige Logik: ``UNKNOWN`` ist Pflicht statt Rateschluss."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ReviewAction(str, Enum):
    """Aktionen, die ein Reviewer auslösen kann (Audit-Log)."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RULEPLAN_CHANGED = "RULEPLAN_CHANGED"
    ENVIRONMENT_EDITED = "ENVIRONMENT_EDITED"
    WORKAREA_EDITED = "WORKAREA_EDITED"
    VISUALIZATION_EDITED = "VISUALIZATION_EDITED"
    RESEND_TO_VISION = "RESEND_TO_VISION"
    MANUAL_HOLD = "MANUAL_HOLD"
    COMMENT_ADDED = "COMMENT_ADDED"


class NvtPosition(str, Enum):
    """Grobe Lage des NVT im Verkehrsraum."""

    ON_SIDEWALK = "on_sidewalk"
    BEHIND_SIDEWALK = "behind_sidewalk"
    IN_DRIVEWAY = "in_driveway"
    IN_GREEN_AREA = "in_green_area"
    ON_PRIVATE_PROPERTY = "on_private_property"
    AT_ROADSIDE = "at_roadside"
    IN_INTERSECTION_AREA = "in_intersection_area"
    IN_CURVE = "in_curve"
    ON_BUSINESS_PREMISES = "on_business_premises"
    UNKNOWN = "unknown"


class RoadClass(str, Enum):
    HAUPTVERKEHR = "hauptverkehr"
    WOHNSTRASSE = "wohnstrasse"
    SACKGASSE = "sackgasse"
    BETRIEBSWEG = "betriebsweg"
    UNKNOWN = "unknown"


class RequiredTrafficArea(str, Enum):
    SIDEWALK_ONLY = "sidewalk_only"
    SIDEWALK_AND_ROAD_STRIP = "sidewalk_and_road_strip"
    ROAD_LANE = "road_lane"
    CYCLEWAY = "cycleway"
    CUL_DE_SAC_FULL_CLOSURE = "cul_de_sac_full_closure"
    PRIVATE_AREA = "private_area"
    UNKNOWN = "unknown"


class PhotoKind(str, Enum):
    """Rolle eines Fotos im Prozess."""

    ORIGINAL = "original"
    ANALYSIS = "analysis"
    PROPOSAL = "proposal"
    FINAL = "final"


class OverlaySymbolType(str, Enum):
    """Zulässige Overlay-Symbole. Renderer prüft, dass ausgewählter
    Regelplan diese Symbole tatsächlich vorsieht (siehe DATA_MODEL.md §2.12).
    """

    WARNBAKE = "warnbake"
    LEITBAKE = "leitbake"
    ABSPERRSCHRANKE = "absperrschranke"
    ABSPERRGITTER = "absperrgitter"
    Z_123 = "z_123"  # Arbeitsstelle
    Z_283 = "z_283"  # Haltverbot
    Z_286 = "z_286"  # eingeschränktes Haltverbot
    HALTVERBOT = "haltverbot"
    ARROW = "arrow"
    TEXT = "text"


class AddressSource(str, Enum):
    USER = "user"
    OCR = "ocr"
    VISION = "vision"
    CSV = "csv"


class LocationSource(str, Enum):
    EXIF = "exif"
    OCR = "ocr"
    USER = "user"
    CSV = "csv"
    GEOCODER = "geocoder"


# Erlaubte Statusübergänge — Guard in nvt_service (siehe REVIEW_PROCESS.md §2)
NVT_STATUS_TRANSITIONS: dict[NvtStatus, set[NvtStatus]] = {
    NvtStatus.NEW: {NvtStatus.ANALYZING, NvtStatus.REJECTED},
    NvtStatus.ANALYZING: {
        NvtStatus.ANALYZED,
        NvtStatus.NEEDS_REVIEW,
        NvtStatus.REJECTED,
    },
    NvtStatus.ANALYZED: {
        NvtStatus.NEEDS_REVIEW,
        NvtStatus.REVIEWED,
    },
    NvtStatus.NEEDS_REVIEW: {
        NvtStatus.REVIEWED,
        NvtStatus.REJECTED,
        NvtStatus.ANALYZING,
    },
    NvtStatus.REVIEWED: {
        NvtStatus.APPROVED,
        NvtStatus.NEEDS_REVIEW,
        NvtStatus.REJECTED,
    },
    NvtStatus.APPROVED: {
        NvtStatus.EXPORTED,
        NvtStatus.NEEDS_REVIEW,
    },
    NvtStatus.EXPORTED: set(),
    NvtStatus.REJECTED: {NvtStatus.NEEDS_REVIEW},
}


def is_valid_transition(current: NvtStatus, target: NvtStatus) -> bool:
    """True, wenn der Übergang laut Tabelle zulässig ist."""
    return target in NVT_STATUS_TRANSITIONS.get(current, set())
