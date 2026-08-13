# ARCHITECTURE — VRA-NVT-Automation

> Systemarchitektur, Tech-Stack, Verzeichnisstruktur, Datenfluss, Deployment.

---

## 1. Systemüberblick

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Web-UI (React + TypeScript)                       │
│  Dashboard | Projekte | NVT-Prüfung | Regelpläne | Referenzen | Audit    │
└──────────────────────────────────────────────────────────────────────────┘
                             │  REST (JSON)
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       FastAPI Application Layer                          │
│    Routes  →  Services  →  Domain  →  Repositories  →  DB / FS / KB      │
└──────────────────────────────────────────────────────────────────────────┘
       │            │             │              │              │
       ▼            ▼             ▼              ▼              ▼
  ┌────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐
  │  OCR   │  │  Vision  │  │Rule Engine│  │ Documents│  │ Knowledge  │
  │adapter │  │provider  │  │  (pure)   │  │(docx/pdf)│  │  Base (FS) │
  └────────┘  └──────────┘  └───────────┘  └──────────┘  └────────────┘
       │           │              │              │              │
       ▼           ▼              ▼              ▼              ▼
  Tesseract     Claude       metadata.json     python-docx   /knowledge/
  (default)     (default)    (versioniert)     Pillow/CV2    (RSA21 …)
```

Kernprinzip: **Alle „intelligenten“ Komponenten sind austauschbare Adapter
hinter Interfaces.** Rule Engine ist rein deterministisch und hat keine
Netzwerk-Abhängigkeit.

---

## 2. Tech-Stack

### Backend
- **Python** 3.11+
- **FastAPI** (Web-Framework, OpenAPI-Doku automatisch)
- **Pydantic v2** (Validierung an allen Grenzen — insbes. LLM-Ausgaben)
- **SQLAlchemy 2** (ORM)
- **Alembic** (DB-Migrationen)
- **SQLite** für lokale Entwicklung, **PostgreSQL** für Produktion
- **uv** oder **Poetry** (Dep-Management; Empfehlung `uv` wegen Geschwindigkeit)
- **pytest** (Tests), **ruff** (Lint/Format), **mypy** (Type-Check)

### PDF / Bild / OCR
- **PyMuPDF (fitz)** — PDF-Text- und Bildextraktion (aus Referenz-PDF, Regelplan-Zeichnungen)
- **Pillow** — Basis-Bildbearbeitung, Overlay-Zeichnen
- **OpenCV** — Kantenerkennung, ggf. Kalibrierung, Perspektiven-Vorverarbeitung
- **Tesseract** (via `pytesseract`) — OCR-Default (offline)

### KI / Vision
- **Provider-Abstraktion** `app/vision/base.py::VisionProvider`
- **Default-Implementierung**: `AnthropicVisionProvider` (Claude Sonnet/Opus mit Vision)
- **Anthropic Python SDK** (`anthropic`)
- **Prompt-Dateien** unter `/prompts/` (versioniert, im Git)

### Dokumentgenerierung
- **python-docx** — Word-Anlage
- **weasyprint** oder **libreoffice --headless** — optionaler PDF-Export
- **Jinja2** — Templates für interne HTML-Reports (nicht für Behördendokument)

### Frontend
- **React 18** + **TypeScript**
- **Vite** (Build)
- **TanStack Query** (Server-State)
- **Zustand** oder **Redux Toolkit** (Client-State, minimal)
- **Tailwind CSS** + **shadcn/ui** (Design-System, unaufdringlich)
- **react-map-gl** oder **Leaflet** (Karte, wenn GPS vorhanden)

### Infrastruktur
- **docker-compose** (backend, frontend, db, optional worker)
- **RQ** oder eigene SQLAlchemy-Job-Queue für Batch-Verarbeitung (Redis optional)
- **.env** für Konfiguration, `.env.example` im Repo

---

## 3. Verzeichnisstruktur

```
/                                    # Repo-Root
├── app/                             # Python-Package (Backend)
│   ├── __init__.py
│   ├── main.py                      # FastAPI-Entry (`uvicorn app.main:app`)
│   ├── config.py                    # Settings via Pydantic-BaseSettings + .env
│   │
│   ├── api/                         # HTTP-Layer
│   │   ├── deps.py                  # DB-Session, Auth (später)
│   │   ├── projects.py              # /api/projects
│   │   ├── nvt.py                   # /api/nvt
│   │   ├── review.py                # /api/review (Freigabe, Änderung)
│   │   ├── ruleplans.py             # /api/ruleplans (CRUD Metadaten)
│   │   ├── knowledge.py             # /api/knowledge (Upload RSA21/lokal)
│   │   ├── uploads.py               # /api/uploads (ZIP/Ordner)
│   │   └── exports.py               # /api/exports (DOCX)
│   │
│   ├── core/                        # Anwendungsdomäne
│   │   ├── models.py                # SQLAlchemy-Tabellen
│   │   ├── schemas.py               # Pydantic-DTOs
│   │   ├── enums.py                 # Status-Enums, ValidCodes
│   │   ├── services/                # Anwendungsfälle (Use Cases)
│   │   │   ├── project_service.py
│   │   │   ├── nvt_service.py
│   │   │   ├── review_service.py
│   │   │   └── export_service.py
│   │   └── repositories/            # Datenzugriff (Repository-Pattern)
│   │       ├── project_repo.py
│   │       ├── nvt_repo.py
│   │       └── audit_repo.py
│   │
│   ├── vision/                      # KI-Adapter
│   │   ├── base.py                  # VisionProvider-Interface
│   │   ├── anthropic_provider.py    # Claude-Implementierung
│   │   ├── schema.py                # strenges JSON-Output-Modell
│   │   └── prompts.py               # Loader für /prompts/*.md (versioniert)
│   │
│   ├── ocr/                         # OCR-Adapter
│   │   ├── base.py                  # OCRProvider-Interface
│   │   ├── tesseract_provider.py    # Default
│   │   └── parsers.py               # NVT-Nummer/Adresse-Regex + Heuristik
│   │
│   ├── classification/              # Umgebungsprofil-Aggregation
│   │   └── environment_builder.py   # kombiniert Vision + OCR + GPS
│   │
│   ├── rules/                       # deterministische Rule Engine (siehe RULE_ENGINE.md)
│   │   ├── engine.py
│   │   ├── predicates.py
│   │   ├── exclusions.py
│   │   ├── candidate_search.py
│   │   └── ranking.py
│   │
│   ├── ruleplans/                   # Regelplan-Bibliothek Loader
│   │   ├── loader.py                # liest /knowledge/regelplaene/**/metadata.json
│   │   ├── validator.py             # prüft Metadaten-Vollständigkeit
│   │   └── similarity.py            # optional (Phase 6+): Referenzfall-Ähnlichkeit
│   │
│   ├── geodata/                     # optional (Phase 5+)
│   │   ├── base.py                  # GeoProvider-Interface
│   │   ├── nominatim_provider.py    # OSM-Nominatim
│   │   └── local_provider.py        # aus CSV/GeoJSON
│   │
│   ├── documents/                   # Word-/PDF-/HTML-Generierung
│   │   ├── word_builder.py          # python-docx, Anlagen-Layout
│   │   ├── html_report.py           # interner Prüfbericht
│   │   ├── pdf_export.py            # optional (Phase 9)
│   │   └── photo_annotate.py        # Overlay auf Foto (Pillow + OpenCV)
│   │
│   ├── visualization/               # Absperrungs-Overlay-Modell
│   │   ├── overlay_model.py         # normalisierte 0-1-Koordinaten
│   │   ├── symbols.py               # Registry für Baken/Schilder-Assets
│   │   └── renderer.py              # Overlay-Modell → gerendertes PNG
│   │
│   ├── validation/                  # QA-Gate vor Export
│   │   └── qa_gate.py               # Prüfliste aus §26 / §52
│   │
│   ├── audit/                       # append-only Entscheidungshistorie
│   │   ├── logger.py                # → DB + audit.jsonl
│   │   └── events.py                # Event-Typen (RULEPLAN_CHANGED, …)
│   │
│   └── workers/                     # Batch-Jobs (Phase 10)
│       ├── queue.py                 # Job-Queue-Adapter
│       └── pipeline_job.py          # End-to-End pro NVT
│
├── prompts/                         # Versionierte LLM-Prompts (Markdown)
│   ├── environment_analysis.md
│   ├── traffic_analysis.md
│   ├── ruleplan_reasoning.md
│   ├── visualization.md
│   └── document_generation.md
│
├── frontend/                        # React + TS + Vite (Phase 7)
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Projects.tsx
│   │   │   ├── NvtReview.tsx        # Herzstück: Foto | Karte | Analyse
│   │   │   ├── RulePlans.tsx
│   │   │   ├── References.tsx
│   │   │   └── Audit.tsx
│   │   ├── api/                     # generierte Client-SDK aus OpenAPI
│   │   ├── components/
│   │   └── styles/
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── knowledge/                       # Regelwerks-Wissensbasis
│   ├── README.md                    # Beschreibt, was hier einzupflegen ist
│   ├── rsa21/                       # Platzhalter (User füllt)
│   ├── stvo/
│   ├── vwv_stvo/
│   ├── ztv_sa/
│   ├── mvas/
│   ├── regelplaene/                 # Regelplan-DB (M2/3 initial gefüllt aus Referenz-PDF)
│   │   ├── VZP1/
│   │   │   ├── plan.pdf
│   │   │   ├── preview.png
│   │   │   └── metadata.json
│   │   ├── B1_2/
│   │   ├── B2_2/
│   │   └── B1_15/
│   ├── referenzfaelle/              # Ergebnis aus Extraktion (Phase 3)
│   │   └── NVT_7107.json            # etc.
│   └── lokale_vorgaben/
│       └── muenster/                # z.B. Standard-Auflagen aus PDF S. 57–58
│
├── data/                            # Laufzeit-Daten (nicht ins Repo)
│   ├── projects/{project_id}/
│   │   ├── input/                   # hochgeladene Fotos
│   │   ├── analyses/                # Zwischenergebnisse pro NVT
│   │   └── exports/                 # generierte DOCX
│   ├── uploads/                     # temporäre ZIPs
│   └── symbols/                     # Bake/Schranke/Schild PNGs für Overlay
│
├── input/                           # (optional) Beispiel-Eingaben für Devs
├── output/                          # (optional) Beispiel-Ausgaben für Devs
│
├── tests/
│   ├── unit/
│   ├── rules/
│   ├── vision/
│   ├── integration/
│   ├── regression/
│   ├── documents/
│   └── fixtures/                    # kleine PNG-/JSON-Fixtures
│
├── scripts/
│   ├── extract_reference_cases.py   # Phase 3
│   └── seed_ruleplans.py            # legt VZP1/B1_2/… aus Referenz-PDF an
│
├── docs/                            # Diese Dokumente (Phase 1)
│   ├── PROJECT_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── RULE_ENGINE.md
│   ├── AI_PIPELINE.md
│   ├── REVIEW_PROCESS.md
│   └── REFERENCE_CASES.md
│
├── alembic/                         # DB-Migrationen (Phase 2)
├── docker-compose.yml               # Phase 12
├── Dockerfile                       # Phase 12
├── pyproject.toml                   # Phase 2
├── .env.example                     # Phase 2
├── Makefile                         # `make dev|test|extract|seed|export`
└── README.md                        # Alt (Bauunternehmen-Website) — bleibt unangetastet
```

**Alt-Bestand des Repos** (`index.html`, `referenzen.html`, `ueber-uns.html`,
`kontakt.html`, `impressum.html`, `datenschutz.html`, `css/`, `js/`, `img/`,
`README.md`) bleibt komplett unangetastet — VRA-System liegt strikt parallel.

---

## 4. Datenfluss End-to-End

```
1. Upload         POST /api/uploads (ZIP oder mehrere Fotos)
                  → gespeichert in data/uploads/{tmp}
                  → Job: "extract & group" in Queue

2. Extraktion     entpackt, ordnet Fotos NVTs zu (Dateiname oder OCR)
                  → schreibt NVT-Records in DB (Status NEW)

3. OCR            pro Foto: Tesseract → NVT-Nummer, Adresse, GPS, Zeit
                  → speichert in Photo.ocr_json

4. NVT-Merge      falls mehrere Photos, gemeinsames NVT-Objekt
                  Konflikte → NEEDS_REVIEW

5. Vision         Provider.analyze_image(photos) → EnvironmentModel (Pydantic)
                  → validiert, in DB persistiert
                  Status: ANALYZING → ANALYZED

6. Rule Engine    engine.decide(environment, geodata, ruleplan_lib)
                  → RulePlanCandidate[] + selected + trace
                  Status: ANALYZED → NEEDS_REVIEW (Default)
                                    oder REVIEWED (bei hoher rule_confidence)

7. Visualization  overlay_model + renderer → proposal.jpg
                  Editor erlaubt manuelle Anpassung

8. Review-UI      User prüft, ändert ggf. Regelplan, gibt frei
                  Jede Änderung → AuditLog
                  Status: NEEDS_REVIEW → APPROVED oder REJECTED

9. QA-Gate        validation.qa_gate.run(project) → OK oder Fehlerliste

10. Export        word_builder.build(project) → VRA_NVT_Gesamt_YYYY-MM-DD.docx
                  Status: APPROVED → EXPORTED
                  Zusätzlich: analysis_report.html (intern)
```

---

## 5. Wichtige architektonische Prinzipien

### 5.1 Klare Trennung
- **`app/api/`** kennt nur `app/core/services/*` — keine direkte DB-Nutzung
- **`app/core/services/`** orchestriert Use Cases — keine HTTP-Details
- **`app/core/repositories/`** kapselt SQLAlchemy — Services bekommen Pydantic-DTOs
- **`app/rules/`** ist eine **reine Funktion** ohne I/O, DB, Netzwerk (deshalb trivial testbar)
- **`app/vision/` und `app/ocr/`** sind austauschbare Adapter hinter Interfaces

### 5.2 Anti-Halluzinations-Guardrails im Code
- **Alle KI-Ausgaben** werden mit Pydantic v2 gegen strenges Schema validiert;
  ungültig → Retry (max. 2×) → sonst `MANUELLE_PRÜFUNG_ERFORDERLICH`
- **Regelplan-Metadaten** werden nur eingelesen, nie generiert
- **Rule Engine** ist die einzige Instanz, die einen Regelplan wählt
- **Confidence-Werte** aus dem LLM landen in `vision_confidence`, gehen **nicht** direkt in Freigabeentscheidungen
- **Jede Quellenangabe** muss auf eine tatsächlich vorhandene Datei in `/knowledge/` verweisen (Validator prüft)

### 5.3 Reproduzierbarkeit
- Jede Entscheidung persistiert:
  - verwendete Regelplan-Version (`ruleset_version`)
  - verwendete KI-Modell-Version (`model_id`, `model_version`)
  - verwendete Prompt-Version (`prompt_hash`)
  - LLM-Rohantwort (im internen Report, nicht im Word)
  - Rule-Engine-Trace
- Regelwerks-Updates ändern **keine** alten Entscheidungen (`Decision.ruleset_version` wird eingefroren)

### 5.4 Datenschutz (DSGVO)
- Fotos gelten als personenbezogene Daten (Gesichter, Kennzeichen)
- **Cloud-KI nur mit Opt-in** (Config-Flag pro Projekt)
- **Lokaler Modus** (Ollama/Tesseract) für sensitive Projekte
- Fotos werden nicht dauerhaft an Anbieter geschickt (nur pro Request, kein Training-Consent)

### 5.5 Erweiterbarkeit
- Neue Regelpläne: `metadata.json` in `/knowledge/regelplaene/{ID}/` ablegen — **keine Codeänderung**
- Neuer Vision-Provider: Klasse implementieren, in Registry eintragen
- Neue lokale Vorgaben: Ordner unter `/knowledge/lokale_vorgaben/{gemeinde}/` mit `manifest.json`

---

## 6. Sicherheit & Zugriff

- **API-Zugang** initial nur lokal (localhost); ab Phase 12 optional Auth (OAuth2 oder API-Key)
- **Uploads** werden mit `python-magic` auf MIME geprüft; nur `image/*`, `application/pdf`, `application/zip`
- **Größenlimits**: 50 MB pro Foto, 500 MB pro ZIP (konfigurierbar)
- **Secrets** nur via ENV; `.env` **nie** ins Git (`.gitignore`)
- **Logs** enthalten keine Foto-Inhalte, keine PII

---

## 7. Deployment (Phase 12)

`docker-compose.yml` mit vier Services:

```yaml
services:
  db:        # PostgreSQL 16
  backend:   # FastAPI + workers (uvicorn --workers 2)
  frontend:  # nginx serviert das Vite-Build
  worker:    # optional, für Batch-Verarbeitung getrennt
```

**Volumes:** `data/`, `knowledge/` extern gemountet (überlebt Container-Neustarts).

**Backup:** täglicher `pg_dump` + `rsync` auf `/data/` und `/knowledge/`.

---

## 8. Nicht in dieser Architektur (bewusst)

- Kein SSR-Framework (Next.js/Remix) — nicht nötig, App ist intern
- Kein GraphQL — REST + generierte OpenAPI-Clients reichen
- Kein separates Micro-Service-Setup — Monolith mit klarer interner Trennung
- Kein Vendor-Lock-in an einen KI-Anbieter — Provider-Pattern zwingend
