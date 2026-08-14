# ARCHITECTURE — VRA-NVT-Automation

> Systemarchitektur, Tech-Stack, Verzeichnisstruktur, Datenfluss.
> **Diese Version spiegelt den tatsächlichen Implementierungsstand nach
> Phase 9 wider** (siehe `docs/CURRENT_STATE.md` für den exakten Stand).
> ✅ = implementiert, ⏳ = geplant, noch nicht gebaut.

---

## 1. Systemüberblick

```
┌──────────────────────────────────────────────────────────────────────────┐
│              Web-UI (React + TypeScript)              ⏳ Phase 7          │
│  Dashboard | Projekte | NVT-Prüfung | Regelpläne | Referenzen | Audit    │
└──────────────────────────────────────────────────────────────────────────┘
                             │  REST (JSON)                    ✅ implementiert
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Application Layer          ✅ implementiert     │
│    Routes  →  Services  →  Domain  →  Repositories  →  DB / FS / KB      │
└──────────────────────────────────────────────────────────────────────────┘
       │            │             │              │              │
       ▼            ▼             ▼              ▼              ▼
  ┌────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐
  │  OCR   │  │  Vision  │  │Rule Engine│  │ Documents│  │ Knowledge  │
  │adapter │  │provider  │  │  (pure)   │  │(docx/html)│ │  Base (FS) │
  │   ✅   │  │    ✅    │  │    ✅     │  │    ✅    │  │     ✅     │
  └────────┘  └──────────┘  └───────────┘  └──────────┘  └────────────┘
       │           │              │              │              │
       ▼           ▼              ▼              ▼              ▼
  Tesseract     Claude       metadata.json    python-docx    /knowledge/
  (default)  (+ Mock für     (versioniert)    + eigener      (RSA21 …
             Tests/Offline)                   HTML-Report    Fachfelder
                                                              vom Nutzer
                                                              zu pflegen)

  Visualisierung (Overlay + Symbol-Rendering)                    ✅
  Batch-Queue / Worker (für 20–500 NVT parallel)               ⏳ Phase 10
```

Kernprinzip: **Alle „intelligenten" Komponenten sind austauschbare Adapter
hinter Interfaces.** Rule Engine ist rein deterministisch und hat keine
Netzwerk-Abhängigkeit. **KI liefert Beobachtungen, nie Entscheidungen.**

---

## 2. Tech-Stack

### Backend — ✅ implementiert
- **Python** 3.11
- **FastAPI** (Web-Framework, OpenAPI-Doku unter `/docs` automatisch)
- **Pydantic v2** (`extra="forbid"` an allen Schema-Grenzen — Anti-
  Halluzinations-Schutz, siehe `app/core/schemas.py`, `app/vision/schema.py`)
- **SQLAlchemy 2** (ORM, `app/core/models.py`)
- **Alembic** (DB-Migrationen, `alembic/`)
- **SQLite** für lokale Entwicklung (`data/dev.db`) — läuft, ist der
  aktuell einzig getestete Modus. **PostgreSQL** ist im Code vorbereitet
  (`pip install .[postgres]`, `psycopg`), aber **ungetestet**.
- **pytest** — 191 Tests, alle grün (Stand siehe `docs/CURRENT_STATE.md`)
- **ruff, mypy** — in `pyproject.toml` konfiguriert, aber noch nicht
  standardmäßig in einen CI-Lauf eingebunden (keine CI vorhanden, Phase 12)

### PDF / Bild / OCR — ✅ implementiert
- **PyMuPDF (`pymupdf`, importiert als `fitz`)** — Extraktion von Fotos
  und Regelplan-Seiten aus der Referenz-PDF (`scripts/extract_reference_cases.py`)
- **Pillow** — Overlay-Rendering (`app/visualization/renderer.py`),
  EXIF-Auslesen (`app/uploads/photo_processor.py`)
- **OpenCV** (`opencv-python-headless`) — als Dependency vorhanden, **aktuell
  nicht aktiv genutzt** (im Master-Prompt für künftige Kalibrierung/
  Kantenerkennung vorgesehen, kein Code dafür bisher)
- **Tesseract** (via `pytesseract`) — OCR-Default, Systempaket
  `tesseract-ocr` + `tesseract-ocr-deu` muss auf dem Host installiert sein
  (in der aktuellen Session bereits installiert; auf neuer Maschine per
  `apt-get install tesseract-ocr tesseract-ocr-deu` nachzuholen)

### KI / Vision — ✅ implementiert
- **Provider-Abstraktion** `app/vision/base.py::VisionProvider` (Protocol)
- **`AnthropicVisionProvider`** (`app/vision/anthropic_provider.py`) —
  Claude mit Vision, Multi-Image in einem Aufruf. Braucht
  `ANTHROPIC_API_KEY`; ohne Key liefert der Analyze-Endpoint HTTP 400.
- **`MockVisionProvider`** (`app/vision/mock_provider.py`) — deterministisch,
  für Tests und Offline-Betrieb (`?provider_override=mock`)
- **Prompt-Dateien** unter `/prompts/*.md`, versioniert per YAML-
  Frontmatter + SHA-256-Hash (`app/vision/prompts.py`). Aktuell ein
  Prompt: `prompts/environment_analysis.md`.

### Dokumentgenerierung — ✅ implementiert
- **python-docx** — Word-Anlage (`app/documents/word_builder.py`)
- **eigener HTML-Report** (`app/documents/html_report.py`, reines
  Python/html-Escaping, kein Template-Engine nötig für diesen Umfang)
- **Kein PDF-Export** (ursprünglich als optional geplant — nicht gebaut,
  nicht angefragt)

### Frontend — ⏳ Phase 7, noch nicht begonnen
Geplant: React 18 + TypeScript + Vite + TanStack Query + Tailwind. Kein
Code existiert bisher. Alle Funktionalität ist aktuell nur über die REST-
API (OpenAPI-Doku unter `/docs`, wenn der Server läuft) bzw. Python-Skripte
nutzbar.

### Infrastruktur — ⏳ größtenteils Phase 10/12
- Kein Docker-Compose, kein Job-Queue-System bisher. Alle Requests
  (Upload, Analyze, Decide, Visualize, Export) laufen **synchron** im
  FastAPI-Request — für einzelne NVT und kleine Test-Batches ausreichend
  performant, für 100+ NVT in einem Rutsch noch nicht ausgelegt
  (Vision-API-Aufrufe sind seriell pro Request).
- `.env` / `.env.example` — ✅ vorhanden, alle Konfig-Werte dokumentiert.

---

## 3. Verzeichnisstruktur (Ist-Zustand)

```
/                                    # Repo-Root
├── app/                             # Python-Package (Backend) — ✅
│   ├── main.py                      # FastAPI-Entry, registriert alle Router
│   ├── config.py                    # Settings (Pydantic-BaseSettings + .env)
│   │
│   ├── api/                         # HTTP-Layer — ✅ alle Endpoints implementiert
│   │   ├── deps.py                  # DB-Session-Dependency, Settings-Dependency
│   │   ├── schemas.py               # API-Response-DTOs (from_attributes)
│   │   ├── projects.py              # POST/GET/DELETE /api/projects
│   │   ├── uploads.py               # POST /api/projects/{id}/uploads
│   │   ├── nvt.py                   # GET /api/projects/{id}/nvts[?status=]
│   │   ├── analyze.py               # POST .../nvts/{id}/analyze
│   │   ├── decide.py                # POST .../nvts/{id}/decide
│   │   ├── visualize.py             # POST .../nvts/{id}/visualize
│   │   └── exports.py               # POST /api/projects/{id}/exports,
│   │                                 # GET .../exports/latest.docx
│   │
│   ├── core/                        # Anwendungsdomäne — ✅
│   │   ├── models.py                # 13 SQLAlchemy-Tabellen
│   │   ├── schemas.py               # ~20 Pydantic-DTOs, extra="forbid"
│   │   ├── enums.py                 # Status-Enums + NVT_STATUS_TRANSITIONS
│   │   ├── db.py                    # Engine/Session-Setup, SQLite-FK-Pragma
│   │   ├── types.py                 # GUID-Typ (SQLite CHAR(36)/PG UUID)
│   │   ├── services/                # Use-Case-Orchestrierung
│   │   │   ├── upload_service.py    # Entpacken→OCR→NVT-Erkennung→DB
│   │   │   └── export_service.py    # QA-Gate→Word+HTML→Export-Row
│   │   └── repositories/            # Reines Datenzugriffs-Layer
│   │       ├── project_repo.py
│   │       ├── nvt_repo.py          # + State-Machine-Guard
│   │       └── audit_repo.py        # append-only
│   │
│   ├── vision/                      # KI-Adapter — ✅
│   │   ├── base.py                  # VisionProvider-Protocol
│   │   ├── anthropic_provider.py    # Claude
│   │   ├── mock_provider.py         # Deterministischer Test-/Offline-Fake
│   │   ├── schema.py                # VisionEnvironmentResponse (strict)
│   │   ├── prompts.py               # Loader für /prompts/*.md
│   │   ├── pipeline.py              # Retry-Kette (3x) + Halluzinations-Postvalidator
│   │   └── aggregator.py            # Multi-Foto-Merge (konservativ)
│   │
│   ├── ocr/                         # OCR-Adapter — ✅
│   │   ├── base.py                  # OCRProvider-Protocol
│   │   ├── tesseract_provider.py
│   │   └── parsers.py               # Regex: NVT-Nr./Adresse/GPS/Datum/Regelplan-Label
│   │
│   ├── uploads/                     # Foto-Import — ✅
│   │   ├── unpack.py                # ZIP (Zip-Slip-Schutz) oder Ordner-Tree
│   │   └── photo_processor.py       # EXIF/GPS, SHA-256, Kopie (Original bleibt)
│   │
│   ├── classification/              # Bindeglied Domäne↔Adapter — ✅
│   │   ├── nvt_detector.py          # Prioritätskette User>Dateiname>Ordner>OCR
│   │   ├── environment_builder.py   # Vision-Pipeline → EnvironmentAnalysis in DB
│   │   ├── decision_builder.py      # Rule Engine → Decision+Candidates in DB
│   │   └── visualization_builder.py # Proposer+Renderer → Visualization in DB
│   │
│   ├── rules/                       # deterministische Rule Engine — ✅ (siehe RULE_ENGINE.md)
│   │   ├── engine.py                # decide() — reine Funktion, kein I/O
│   │   ├── predicates.py            # 24 benannte Prädikate, Ternary-Semantik
│   │   ├── candidate_search.py      # geeignet_fuer-Matching gegen Prädikate
│   │   ├── exclusions.py            # 5 harte Sofort-Ausschlüsse
│   │   └── ranking.py               # Score-Berechnung + Tiebreak
│   │
│   ├── ruleplans/                   # Regelplan-Bibliothek — ✅
│   │   └── loader.py                # RulePlanLibrary, berechnet is_complete selbst
│   │
│   ├── reference_cases/             # Referenzfall-Bibliothek — ✅
│   │   └── loader.py                # ReferenceCaseLibrary (Regressionstests, Similarity später)
│   │
│   ├── visualization/               # Absicherungs-Overlay — ✅
│   │   ├── symbols.py               # SymbolRegistry (lädt data/symbols/*.png)
│   │   ├── proposer.py              # Overlay-Vorschlag aus Env+Regelplan
│   │   └── renderer.py              # Zeichnet auf Foto-Kopie → proposal.jpg
│   │
│   ├── validation/                  # QA-Gate — ✅
│   │   └── qa_gate.py               # 8 Prüfungen vor Export
│   │
│   ├── documents/                   # Dokument-Generierung — ✅
│   │   ├── word_builder.py          # DOCX (keine Debug-/Confidence-Infos!)
│   │   └── html_report.py           # Interner Bericht (alles Debug-Relevante)
│   │
│   ├── geodata/                     # ⏳ nicht gebaut (Nominatim-Geocoding geplant)
│   └── workers/                     # ⏳ nicht gebaut (Batch-Queue, Phase 10)
│
├── prompts/                         # Versionierte LLM-Prompts — ✅ (1 von geplant ~5)
│   └── environment_analysis.md      # ⏳ traffic_analysis.md, ruleplan_reasoning.md,
│                                     #    visualization.md, document_generation.md fehlen
│                                     #    (bisher nicht gebraucht — Word-Text wird
│                                     #    deterministisch aus DB-Daten gebaut, nicht per LLM)
│
├── frontend/                        # ⏳ Phase 7 — Ordner existiert noch nicht
│
├── knowledge/                       # Regelwerks-Wissensbasis — ✅ Struktur + Metadaten
│   ├── README.md
│   ├── regelplaene/                 # ✅ 4 Ordner (VZP1, B1_2, B2_2, B1_15)
│   │   └── {ID}/metadata.json       # ⚠️ Fachfelder LEER — Fachanwender-Pflicht,
│   │                                #    siehe docs/CURRENT_STATE.md
│   ├── referenzfaelle/              # ✅ 26 NVT-Ordner (7101–7126) mit nvt.json
│   │                                #    Fotos NICHT im Git (per .gitignore),
│   │                                #    entstehen per scripts/extract_reference_cases.py
│   ├── rsa21/, stvo/, vwv_stvo/,
│   │   ztv_sa/, mvas/               # ⏳ leer, warten auf Fachanwender-Upload
│   └── lokale_vorgaben/             # ⏳ leer (Standard-Auflagen Münster noch
│                                     #    nicht strukturiert eingepflegt, nur in
│                                     #    docs/REFERENCE_CASES.md §5 dokumentiert)
│
├── data/                            # Laufzeit-Daten
│   ├── symbols/                     # ✅ 10 generierte PNG-Symbole (im Git!)
│   ├── dev.db                       # SQLite (gitignored)
│   ├── projects/{id}/               # Uploads, Visualisierungen, Exports (gitignored)
│   └── uploads/                     # temporäre Upload-Staging-Ordner (gitignored)
│
├── tests/                           # ✅ 24 Testdateien, 191 Tests, flache Struktur
│                                     #    (keine unit/rules/vision/integration-Unterordner
│                                     #    wie ursprünglich geplant — alles direkt in tests/)
│
├── scripts/
│   ├── bootstrap_knowledge.py       # ✅ erzeugt initiale referenzfaelle/regelplaene-JSONs
│   ├── extract_reference_cases.py   # ✅ PyMuPDF-Extraktion aus Referenz-PDF
│   ├── generate_symbols.py          # ✅ erzeugt data/symbols/*.png
│   └── create_sample_project.py     # ✅ Bootstrap-Skript für Dev-DB
│
├── docs/                            # ✅ alle 7 Phase-1-Dokumente + CURRENT_STATE.md
├── alembic/                         # ✅ 1 Migration (initial schema)
├── pyproject.toml                   # ✅
├── .env.example                     # ✅
├── Makefile                         # ✅ install-dev|migrate|test|dev|sample|revision
├── CLAUDE.md                        # ✅ Projektregeln für Claude Code
│
└── # Alt-Bestand (unangetastet):
    index.html, referenzen.html, ueber-uns.html, kontakt.html,
    impressum.html, datenschutz.html, css/, js/, img/, README.md
```

---

## 4. Datenfluss (Ist-Zustand — synchron, kein Queue)

```
1. Upload         POST /api/projects/{id}/uploads (Multi-File oder 1 ZIP)
                  → gespeichert in data/projects/{id}/input/
                  → UploadService: entpacken → OCR (optional) →
                    NvtDetector (Prioritätskette) → Nvt+Photo-Rows in DB
                  Status: NEW  (mehrere Fotos desselben NVT ergänzen
                  denselben Datensatz statt Duplikat)

2. Analyze         POST .../nvts/{id}/analyze  (einzeln pro NVT, vom
                  Client/UI aufzurufen — kein automatischer Trigger nach
                  Upload)
                  → VisionPipeline (Retry×3) → EnvironmentAnalysis in DB
                  Status: NEW → ANALYZING → ANALYZED oder NEEDS_REVIEW
                  (NEEDS_REVIEW z.B. wenn Mock/Vision "unknown" liefert)

3. Decide          POST .../nvts/{id}/decide
                  → RulePlanLibrary laden → app.rules.decide() (pure
                    Funktion) → Decision + RulePlanCandidate-Rows in DB
                  Status: → NEEDS_REVIEW (immer — auch bei
                  AUTO_FREIGABE_VORBEREITET; Mensch muss bestätigen)

4. Visualize       POST .../nvts/{id}/visualize
                  → Proposer erzeugt Overlay-Modell aus Env+Regelplan
                  → Renderer zeichnet auf Foto-Kopie → *_proposal.jpg
                  → Visualization+Photo(PROPOSAL)-Row in DB
                  (Privatfläche-Fälle: kein Overlay nötig, übersprungen)

5. Freigabe        ⏳ Kein API-Endpoint für "Freigeben" bisher — würde in
                  Phase 7 (Review-UI) dazukommen. Aktuell nur möglich per
                  direktem DB-Zugriff (Review-Row + Statuswechsel über
                  NvtRepo.update_status), wie im Demo-Skript gezeigt
                  (siehe docs/CURRENT_STATE.md).
                  Ziel-Status: NEEDS_REVIEW → REVIEWED → APPROVED

6. Export          POST /api/projects/{id}/exports [?dry_run=&require_review=]
                  → QaGate (8 Prüfungen) → bei Erfolg:
                    word_builder.build() + html_report.build()
                  → Export-Row in DB, vorherige Exports superseded=true
                  Status: APPROVED → EXPORTED
                  GET .../exports/latest.docx zum Download
```

**Wichtiger Unterschied zum ursprünglichen Phase-1-Plan:** Es gibt noch
keinen automatischen Pipeline-Trigger ("Upload → alles läuft durch").
Jeder Schritt (Analyze/Decide/Visualize) ist ein expliziter API-Call. Das
ist für Einzeltests und die kommende Review-UI (die ohnehin Schritt für
Schritt anzeigen will) ausreichend, aber für Batch-Verarbeitung von 100+
NVT fehlt noch die Orchestrierung (Phase 10).

---

## 5. Wichtige architektonische Prinzipien

### 5.1 Klare Trennung — ✅ eingehalten
- `app/api/` kennt nur Repositories/Services/Builder — keine Business-Logik
- `app/rules/` ist eine **reine Funktion** ohne I/O (`decide()` nimmt
  Pydantic-Schemas, gibt Pydantic-Dataclasses zurück — komplett ohne DB-
  oder Netzwerkzugriff, dadurch in <1s vollständig testbar)
- `app/vision/` und `app/ocr/` sind Adapter hinter Protocol-Interfaces;
  Austausch von Claude gegen einen anderen Provider erfordert nur eine
  neue Klasse, keine Änderung an Pipeline/Builder/API

### 5.2 Anti-Halluzinations-Guardrails — ✅ im Code verankert
- `VisionEnvironmentResponse` (Pydantic, `extra="forbid"`) hat **kein**
  Feld für Regelplan-Vorschläge — selbst wenn das Modell einen nennt,
  wird die Antwort beim Parsen abgelehnt
- Freitextfelder (`existing_signs`, `uncertainties`, …) laufen durch einen
  Regex-Postvalidator, der Regelplan-Nennungen und RSA-Zitate entfernt
  und als Warnung protokolliert (`app/vision/pipeline.py::_postvalidate`)
- `RulePlanLibrary` berechnet `is_complete` **selbst** aus Feld-
  Vollständigkeit, glaubt nicht dem JSON-Wert
- Ein Regelplan mit `is_complete=False` kann nie zu
  `AUTO_FREIGABE_VORBEREITET` führen (`rule_confidence` wird auf 0.5
  gedeckelt, siehe `app/rules/engine.py::_rule_confidence`)
- Word-Export enthält nachweislich (per Test, `tests/test_export.py`)
  keine Confidence-Werte, Modell-IDs, Prompt-Hashes oder Rohantworten

### 5.3 Reproduzierbarkeit — ✅ implementiert
- `EnvironmentAnalysis` und `Decision` speichern `model_id`,
  `model_version`, `prompt_hash`, `ruleset_version`
- `RulePlanEntry.revision_hash` = SHA-256 der `metadata.json` — jede
  Änderung an einem Regelplan ist versioniert nachvollziehbar
- Exportierte Word-Dateien werden nicht überschrieben; ein erneuter
  Export markiert den vorherigen als `superseded=True` und legt eine neue
  Versionsdatei an (`VRA_NVT_Gesamt_{datum}_v{n}.docx`)

### 5.4 Datenschutz (DSGVO) — ⏳ teilweise
- ✅ Originalfotos werden nie überschrieben oder verändert
- ✅ `AnthropicVisionProvider` wird nur aktiv, wenn `ANTHROPIC_API_KEY`
  gesetzt ist — ohne Key läuft alles über Mock/lokal
- ⏳ Kein Projekt-Flag `use_cloud_vision` (aus AI_PIPELINE.md §10) bisher
  implementiert — die Entscheidung Cloud/lokal hängt aktuell nur am
  global gesetzten `VISION_PROVIDER`, nicht pro Projekt konfigurierbar
- ⏳ Keine Anonymisierung/Blur-Vorverarbeitung vor Cloud-Upload

### 5.5 Erweiterbarkeit — ✅ wie geplant
- Neuer Regelplan: Ordner + `metadata.json` unter
  `knowledge/regelplaene/{ID}/` — kein Code-Change, `RulePlanLibrary.load()`
  findet ihn automatisch beim nächsten Request
- Neuer Vision-Provider: `VisionProvider`-Protocol implementieren, in
  `app/api/analyze.py` bei `provider_name` ergänzen

---

## 6. Sicherheit & Zugriff — Ist-Zustand

- API läuft nur lokal (`127.0.0.1:8000` per Default), kein Auth
- Uploads: Größenlimits im Code (100 MB/Datei, 1 GB/Request,
  `app/api/uploads.py`), aber **kein** MIME-Check via `python-magic`
  (nur Datei-Endung-basierte Zuordnung in `photo_processor.py`) — das im
  Architektur-Plan erwähnte `python-magic` ist nicht implementiert
- Secrets nur via `.env` (nicht im Git)
- Zip-Slip-Schutz beim ZIP-Entpacken ist implementiert und getestet

---

## 7. Nicht gebaut / bewusst zurückgestellt

- Kein Docker-Compose, kein Dockerfile (Phase 12)
- Kein Batch-Queue-System (Phase 10) — Analyze/Decide/Visualize sind
  synchron pro NVT, kein Bulk-Endpoint
- Kein Geodata-Provider (Nominatim) — Adressen kommen nur aus OCR/EXIF/
  User-Eingabe, keine Rückwärts-Geokodierung
- Kein Similarity-Search zwischen Referenzfällen (in RULE_ENGINE.md als
  optional beschrieben, `ReferenceCaseLibrary` existiert nur als reiner
  Datenzugriff, keine Ähnlichkeitsberechnung)
- Keine Freigabe-API (Review-Endpoint) — kommt mit Phase 7
- Kein PDF-Export (nur Word)
- Kein Auth/Multi-User — `user`-Felder in der API sind optionale
  Query-Parameter, kein echtes Login
