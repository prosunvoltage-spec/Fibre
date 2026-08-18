# DATA_MODEL — VRA-NVT-Automation

> Fachliches Datenmodell (Pydantic-Schemas) + Persistenz-Mapping (SQLAlchemy).
> Alle Entities aus Build-Prompt §9, plus Ergänzungen die aus dem Workflow
> folgen. Konvention: Pydantic-Schema `XxxSchema` für IO/DTO,
> SQLAlchemy-Modell `Xxx` für Tabelle.

Alle Enums in `app/core/enums.py`.

---

## 1. Enums

```python
class NvtStatus(str, Enum):
    NEW           = "NEW"
    ANALYZING     = "ANALYZING"
    ANALYZED      = "ANALYZED"
    NEEDS_REVIEW  = "NEEDS_REVIEW"
    REVIEWED      = "REVIEWED"
    APPROVED      = "APPROVED"
    REJECTED      = "REJECTED"
    EXPORTED      = "EXPORTED"

class DecisionCode(str, Enum):
    AUTO_FREIGABE_VORBEREITET   = "AUTO_FREIGABE_VORBEREITET"
    AUTO_VORSCHLAG              = "AUTO_VORSCHLAG"
    MANUELLE_PRUEFUNG           = "MANUELLE_PRUEFUNG_ERFORDERLICH"
    NICHT_BEURTEILBAR           = "NICHT_BEURTEILBAR"
    REGELPLAN_NICHT_GEFUNDEN    = "REGELPLAN_NICHT_GEFUNDEN"
    WIDERSPRUCH                 = "WIDERSPRUCH_ZWISCHEN_QUELLEN"
    PRIVATFLAECHE               = "PRIVATFLAECHE_KEINE_OEFFENTLICHE_VRA"

class TrafficUser(str, Enum):
    PEDESTRIAN       = "pedestrians"
    CYCLIST          = "cyclists"
    MOTOR_VEHICLE    = "motor_vehicles"
    PUBLIC_TRANSPORT = "public_transport"
    EMERGENCY        = "emergency_vehicles"
    RESIDENTIAL_ACCESS = "residential_access"

class Ternary(str, Enum):
    YES     = "yes"
    NO      = "no"
    UNKNOWN = "unknown"     # Pflicht statt Rateschluss

class ReviewAction(str, Enum):
    APPROVED           = "APPROVED"
    REJECTED           = "REJECTED"
    RULEPLAN_CHANGED   = "RULEPLAN_CHANGED"
    ENVIRONMENT_EDITED = "ENVIRONMENT_EDITED"
    WORKAREA_EDITED    = "WORKAREA_EDITED"
    RESEND_TO_VISION   = "RESEND_TO_VISION"
    MANUAL_HOLD        = "MANUAL_HOLD"
```

---

## 2. Kern-Entities

### 2.1 Project
Ein Auftrag / eine Baumaßnahme.

```python
class ProjectSchema(BaseModel):
    id: UUID
    name: str                              # z.B. "Roxel Einblasarbeiten 2026"
    location_label: str | None             # "Münster-Roxel"
    period_start: date | None
    period_end: date | None
    client: str | None                     # z.B. "Stadtnetze Münster"
    contractor: str                        # eigene Firma
    site_manager_name: str | None
    on_site_responsible_name: str | None
    on_site_responsible_phone: str | None
    ruleset_version: str                   # eingefroren beim Anlegen
    vision_provider: str                   # eingefroren
    created_at: datetime
    updated_at: datetime
```

### 2.2 NVT (Netzverteilerschrank)
Kern-Aggregat.

```python
class NvtSchema(BaseModel):
    id: UUID
    project_id: UUID
    nvt_number: str                        # z.B. "7107", zentrale fachliche ID
    address: AddressSchema | None
    location: LocationSchema | None
    photos: list[PhotoSchema]              # 1..n Fotos
    environment_analysis: EnvironmentAnalysisSchema | None
    work_area: WorkAreaSchema | None
    traffic_users: list[TrafficUserAssessmentSchema]
    ruleplan_candidates: list[RulePlanCandidateSchema]
    decision: DecisionSchema | None
    visualization: VisualizationSchema | None
    review: ReviewSchema | None
    status: NvtStatus
    warnings: list[str] = []
    duplicates_of: UUID | None = None      # für Deduplizierung
    created_at: datetime
    updated_at: datetime
```

**Constraints:**
- (`project_id`, `nvt_number`) unique
- Statusübergänge folgen der State-Machine aus REVIEW_PROCESS.md

### 2.3 Address

```python
class AddressSchema(BaseModel):
    street: str | None
    house_number: str | None
    postal_code: str | None
    city: str | None
    country: str = "DE"
    raw: str | None                        # Original-OCR-Text
    source: Literal["user", "ocr", "vision", "csv"] | None
```

### 2.4 Location (GPS)

```python
class LocationSchema(BaseModel):
    latitude: Decimal | None               # WGS84
    longitude: Decimal | None
    accuracy_meters: Decimal | None
    source: Literal["exif", "ocr", "user", "csv", "geocoder"] | None
    geocoder_name: str | None              # z.B. "nominatim"
    geocoded_at: datetime | None
```

### 2.5 Photo

```python
class PhotoSchema(BaseModel):
    id: UUID
    nvt_id: UUID
    filename: str                          # original filename
    stored_path: str                       # data/projects/{pid}/input/{nvt}/xx.jpg
    mime_type: str
    width: int
    height: int
    sha256: str                            # für Deduplizierung
    exif: dict                             # Kamera-Meta
    ocr_json: dict | None                  # geparste OCR-Rohausgabe
    kind: Literal["original", "analysis", "proposal", "final"] = "original"
    created_at: datetime
```

Die Varianten `analysis / proposal / final` werden **neu** als eigene Photo-Records
gespeichert; das Original bleibt unverändert (Master-Prompt §14, Build-Prompt §78).

### 2.6 EnvironmentAnalysis
Strukturierte Umgebungserkennung aus 1..n Fotos (Vision-Aggregation).

```python
class EnvironmentAnalysisSchema(BaseModel):
    nvt_id: UUID
    # Verkehrsraum (Ternary — nie geraten)
    road_present:                  Ternary
    sidewalk_present:              Ternary
    cycleway_present:              Ternary
    shared_cycle_footway_present:  Ternary
    parking_lane_present:          Ternary
    seiten_streifen_present:       Ternary
    private_property:              Ternary
    business_property:             Ternary          # Stadtwerke/Stadtnetze etc.
    driveway_present:              Ternary
    intersection_present:          Ternary
    junction_present:              Ternary
    cul_de_sac:                    Ternary
    curve_present:                 Ternary
    bus_stop_nearby:               Ternary
    fire_access:                   Ternary

    # NVT-Lage
    nvt_position: Literal[
        "on_sidewalk", "behind_sidewalk", "in_driveway",
        "in_green_area", "on_private_property",
        "at_roadside", "in_intersection_area", "in_curve",
        "on_business_premises", "unknown"
    ]

    # Straßenkategorie (aus Vision + Geodaten)
    road_class: Literal["hauptverkehr", "wohnstrasse", "sackgasse", "betriebsweg", "unknown"]

    # Breiten in Metern — Optional, UNKNOWN wenn nicht zuverlässig
    sidewalk_width_m: Decimal | None
    roadway_width_m: Decimal | None
    cycleway_width_m: Decimal | None
    distance_nvt_to_road_m: Decimal | None

    # weitere Beobachtungen
    parked_vehicles_in_workarea: Ternary
    existing_signs: list[str] = []
    existing_barriers: list[str] = []
    obstacles: list[str] = []
    sight_relations_affected: Ternary

    # Meta
    contributing_photos: list[UUID]        # welche Fotos aggregiert wurden
    vision_confidence: Decimal             # 0..1 vom Provider
    data_completeness: Decimal             # 0..1, wieviele Felder != UNKNOWN
    contradictions: list[str] = []         # bei Multi-Foto-Widersprüchen
    raw_provider_output: dict              # für Audit; nicht ins Word
    model_id: str
    model_version: str | None
    prompt_hash: str                       # SHA256 des verwendeten Prompts
    created_at: datetime
```

### 2.7 WorkArea
Geplanter Arbeitsbereich (Bulli-Position, Einblasgerät, Absperrfläche).

```python
class WorkAreaSchema(BaseModel):
    nvt_id: UUID

    # Fahrzeug/Gerät
    bulli_position: OverlayShapeSchema | None
    bulli_length_m: Decimal = Decimal("5.5")   # Default für VW T6 o.ä., konfigurierbar
    bulli_width_m: Decimal = Decimal("2.0")
    equipment_position: OverlayShapeSchema | None

    # Absperrfläche (Foto-relative Koordinaten)
    barrier_polygon: list[OverlayPointSchema]
    required_traffic_area: Literal[
        "sidewalk_only", "sidewalk_and_road_strip", "road_lane",
        "cycleway", "cul_de_sac_full_closure", "private_area", "unknown"
    ]

    # Betroffene Flächen (Bool statt Ternary — wird aus Environment abgeleitet)
    affects_sidewalk: bool
    affects_road: bool
    affects_cycleway: bool
    affects_driveway: bool
    affects_bus_stop: bool

    # Restfahrbahnbreite (Anforderung aus Auflagen: min. 3,00 m)
    remaining_roadway_width_m: Decimal | None
    remaining_sidewalk_width_m: Decimal | None

    edited_by_user: bool = False
    edited_at: datetime | None
```

### 2.8 TrafficUserAssessment
Pro Verkehrsart eine Bewertung (Build-Prompt §19).

```python
class TrafficUserAssessmentSchema(BaseModel):
    nvt_id: UUID
    user: TrafficUser
    affected: bool
    current_route: str | None
    proposed_route: str | None             # z.B. "über gegenüberliegenden Gehweg"
    safe: Ternary
    reason: str | None
    source_document: str | None            # z.B. "RSA21 Teil B Abschnitt 2.4.3"
```

### 2.9 RulePlan
Ein Eintrag der Regelplan-Bibliothek. Kommt aus `/knowledge/regelplaene/`.

```python
class RulePlanSchema(BaseModel):
    id: str                                # "B1/2", "B2/2", "VZP1", "B1/15"
    name: str                              # "Regelplan B I/2 modifiziert"
    quelle: str                            # z.B. "RSA 21 Teil D"
    version: str                           # "08.21"
    beschreibung: str

    plan_pdf_path: str                     # /knowledge/regelplaene/B1_2/plan.pdf
    preview_png_path: str

    verkehrsraum: list[str]                # z.B. ["innerorts", "gehweg", "fahrbahn_randbereich"]
    geeignet_fuer: list[str]               # z.B. ["arbeit_seitenraum", "arbeit_gehweg"]
    voraussetzungen: list[RequirementSchema]
    ausschlusskriterien: list[RequirementSchema]

    fussverkehr: dict                      # z.B. {"führung": "auf_notweg", "min_breite_m": 1.2}
    radverkehr: dict
    fahrverkehr: dict

    besondere_hinweise: list[str]

    revision_hash: str                     # SHA256 der metadata.json — für Versionierung
    is_complete: bool                      # False solange Pflichtfelder leer
```

**Wichtig:** Wenn ein Regelplan `is_complete = False` hat, wird er in der
Rule Engine **nur als Kandidat** angezeigt, führt aber **niemals** zu
`AUTO_VORSCHLAG` oder `AUTO_FREIGABE_VORBEREITET`.

```python
class RequirementSchema(BaseModel):
    condition: str                         # menschenlesbar
    machine_predicate: str | None          # optional: name aus predicates.py
    source_document: str                   # PFLICHT (Halluzinations-Schutz)
    source_reference: str                  # "Abschnitt 2.4.3 Absatz 2"
    source_page: int | None
    notes: str | None
```

### 2.10 RulePlanCandidate
Vorschlag der Rule Engine für einen konkreten NVT.

```python
class RulePlanCandidateSchema(BaseModel):
    ruleplan_id: str
    matched_predicates: list[str]          # welche Prädikate passten
    unmet_requirements: list[str]          # Voraussetzungen, die nicht (sicher) erfüllt sind
    triggered_exclusions: list[str]        # Ausschlusskriterien, die anschlugen
    score: Decimal                         # 0..1, Ranking innerhalb der Kandidaten
    rank: int                              # 1 = bester Vorschlag
    trace: list[str]                       # menschenlesbarer Ableitungspfad
```

### 2.11 Decision
Die endgültige (vorgeschlagene oder freigegebene) Entscheidung.

```python
class DecisionSchema(BaseModel):
    nvt_id: UUID
    selected_ruleplan_id: str | None       # None wenn PRIVATFLAECHE etc.
    code: DecisionCode
    vision_confidence: Decimal
    rule_confidence: Decimal
    data_completeness: Decimal
    human_review_required: bool
    reasons: list[str]                     # positive Begründung
    warnings: list[str]
    ruleset_version: str                   # eingefroren
    ruleplan_revision_hash: str | None
    model_id: str
    prompt_hash: str
    trace_json: dict                       # kompletter Rule-Engine-Trace
    created_at: datetime
```

### 2.12 Visualization
Overlay-Modell der Absperrung.

```python
class OverlayPointSchema(BaseModel):
    x: Decimal                             # 0..1 relativ zur Bildbreite
    y: Decimal                             # 0..1 relativ zur Bildhöhe

class OverlayShapeSchema(BaseModel):
    kind: Literal["rect", "polygon", "line"]
    points: list[OverlayPointSchema]
    rotation: Decimal = Decimal("0")

class OverlaySymbolSchema(BaseModel):
    type: Literal[
        "warnbake", "leitbake", "absperrschranke", "absperrgitter",
        "z_123", "z_283", "z_286", "haltverbot",
        "arrow", "text"
    ]
    x: Decimal                             # 0..1
    y: Decimal
    rotation: Decimal = Decimal("0")
    scale: Decimal = Decimal("1")
    label: str | None

class VisualizationSchema(BaseModel):
    nvt_id: UUID
    base_photo_id: UUID
    symbols: list[OverlaySymbolSchema]
    shapes: list[OverlayShapeSchema]       # Absperrfläche, Bulli, Notweg
    rendered_photo_id: UUID | None         # generierte proposal.jpg
    final_photo_id: UUID | None            # nach Freigabe erzeugtes final.jpg
    edited_by_user: bool = False
    edited_at: datetime | None
```

**Regel:** In `symbols` dürfen **nur** Typen vorkommen, die im
ausgewählten Regelplan (`Decision.selected_ruleplan_id`) belegt sind.
Renderer prüft das und wirft `VisualizationValidationError`, wenn nicht.

### 2.13 Review
Fachliche Prüfung durch Menschen.

```python
class ReviewSchema(BaseModel):
    nvt_id: UUID
    reviewer: str                          # User-ID oder Name
    action: ReviewAction
    comment: str | None
    before: dict                           # Snapshot vor Änderung (JSON)
    after: dict                            # Snapshot nach Änderung (JSON)
    timestamp: datetime
```

### 2.14 Export

```python
class ExportSchema(BaseModel):
    id: UUID
    project_id: UUID
    docx_path: str
    pdf_path: str | None
    included_nvt_ids: list[UUID]
    qa_gate_report: dict                   # Ergebnis der QA-Checks
    generated_by: str
    generated_at: datetime
```

### 2.15 AuditLog
Append-only.

```python
class AuditLogSchema(BaseModel):
    id: int                                # auto-increment
    timestamp: datetime
    user: str | None                       # None = System
    project_id: UUID | None
    nvt_id: UUID | None
    action: str                            # z.B. "RULEPLAN_CHANGED"
    old_value: str | None
    new_value: str | None
    ruleset_version: str
    model_id: str | None
    payload: dict                          # Freiform, für Kontext
```

Zusätzlich: Datei-Backup `data/audit.jsonl` (append-only, ein Objekt pro Zeile) —
Redundanz gegen versehentliche DB-Bereinigung.

---

## 3. SQLAlchemy-Mapping (Skizze)

```python
# app/core/models.py
class Project(Base):
    __tablename__ = "projects"
    id             = Column(GUID, primary_key=True, default=uuid4)
    name           = Column(String, nullable=False)
    ...
    nvts           = relationship("Nvt", back_populates="project", cascade="all,delete")

class Nvt(Base):
    __tablename__ = "nvts"
    __table_args__ = (UniqueConstraint("project_id", "nvt_number"),)
    id             = Column(GUID, primary_key=True, default=uuid4)
    project_id     = Column(GUID, ForeignKey("projects.id"))
    nvt_number     = Column(String, nullable=False, index=True)
    status         = Column(Enum(NvtStatus), default=NvtStatus.NEW, index=True)
    address_json   = Column(JSON)          # Address ist Value-Object → JSON
    location_json  = Column(JSON)          # dito
    warnings_json  = Column(JSON, default=list)
    duplicates_of  = Column(GUID, ForeignKey("nvts.id"), nullable=True)
    created_at     = Column(DateTime, default=utcnow)
    updated_at     = Column(DateTime, default=utcnow, onupdate=utcnow)

    photos              = relationship("Photo", back_populates="nvt")
    environment         = relationship("EnvironmentAnalysis", uselist=False, back_populates="nvt")
    work_area           = relationship("WorkArea", uselist=False, back_populates="nvt")
    ruleplan_candidates = relationship("RulePlanCandidate", back_populates="nvt")
    decision            = relationship("Decision", uselist=False, back_populates="nvt")
    visualization       = relationship("Visualization", uselist=False, back_populates="nvt")
    reviews             = relationship("Review", back_populates="nvt")
```

Weitere Tabellen analog. **Value-Objects** (Address, Location, EnvironmentAnalysis
mit vielen Skalar-Feldern) werden als JSON-Spalten in Nvt oder als eigene
Tabellen mit 1:1-Relation persistiert (Ermessensfrage — für schnelle Iteration
in Phase 2 → JSON, für Reporting später ggf. eigene Tabelle).

**RulePlan** wird **nicht** in der DB persistiert — die Bibliothek lebt im
Dateisystem unter `/knowledge/regelplaene/`. `RulePlanCandidate` referenziert
den Regelplan über seine `id` (String) + `revision_hash`.

---

## 4. Migration & Seed

**Alembic:**
- `alembic/versions/001_init.py` — alle Tabellen aus Phase 2
- weitere Migrationen additiv; **niemals** destruktive Änderungen ohne Datenmigration

**Seed:**
- `scripts/seed_ruleplans.py` — extrahiert VZP-1, B I/2, B II/2, B I/15 aus Referenz-PDF
  (Seiten 53–56) und legt Grundgerüst `metadata.json` mit `is_complete=False` an
- `scripts/extract_reference_cases.py` — legt `/knowledge/referenzfaelle/NVT_71xx.json`
  + Fotos aus der PDF an

---

## 5. Datenschutz-Anmerkungen

- **Fotos** enthalten oft Kennzeichen und Personen → gelten als personenbezogen
- **Speicherpfade** enthalten keine Klarnamen; Zugriff über UUID
- **Löschkonzept:** Projekt-Löschung entfernt kaskadierend alle NVT, Photos, Files
- **Export-Metadaten** werden aus dem finalen Word ausgeschlossen (kein `Author`,
  kein `LastModifiedBy` — `docx.core_properties` bewusst neutral)

---

## 6. Validierungs-Regeln (Beispiele)

- `NvtStatus.APPROVED` erfordert `Decision.human_review_required == False`
  ODER mindestens 1 `Review.action == APPROVED`
- `Visualization.symbols[i].type` muss in
  `RulePlan.allowed_symbols` enthalten sein (per Loader-Zeit-Check)
- `EnvironmentAnalysis.data_completeness` = 1 - (Anzahl `UNKNOWN`-Felder / Gesamtfelder)
- `Decision.rule_confidence < 0.7` → `human_review_required = True`
- Wenn `Ternary.UNKNOWN` in einem für die Regelauswahl **benötigten** Feld →
  `DecisionCode.MANUELLE_PRUEFUNG`

Diese Regeln stehen als Pydantic-`model_validator` bzw. als Service-Guards
in `app/core/services/`.
