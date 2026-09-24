# PROJECT_PLAN — VRA-NVT-Automation

> Meilensteine, Phasen und Abnahmekriterien für die Automatisierung technischer
> Unterlagen für verkehrsrechtliche Anordnungen (VRA) bei
> Glasfaser-Einblasarbeiten an Netzverteilerschränken (NVT).

---

## 1. Zielbild in einem Satz

Aus einem Ordner mit NVT-Fotos entsteht eine geprüfte, freigegebene Word-Anlage
für die VRA — nachvollziehbar, konservativ, mit menschlicher Freigabe. Das
behördliche Anschreiben wird **nicht** erzeugt (macht die Behörde selbst).

## 2. Kern-Formel

```
Computer Vision + OCR/GPS + Verkehrsmodell + Rule Engine
+ Regelplan-Datenbank + Referenzfall-Datenbank
+ menschliche Freigabe + Word-Generator
= automatisierte VRA-Anlage
```

## 3. Prioritätsreihenfolge (verbindlich)

1. **Fachliche Sicherheit** — nie eine unsichere Zuordnung als sicher ausspielen
2. **Nachvollziehbarkeit** — jede Entscheidung mit Quelle & Trace
3. **Regelkonformität** — nur eingespeiste Regelwerke, nichts halluziniert
4. **Menschliche Kontrolle** — Human-in-the-Loop ist Pflicht, nicht Option
5. **Reproduzierbarkeit** — deterministische Rule Engine, versionierte Regeln
6. **Automatisierung** — soviel wie sicher möglich
7. **Geschwindigkeit** — zuletzt

Geschwindigkeit steht **nie** vor fachlicher Sicherheit. Im Zweifel:
`MANUELLE_PRÜFUNG_ERFORDERLICH`.

---

## 4. Phasen-Roadmap (aus Build-Prompt §70)

Jede Phase ist eigenständig abnahmefähig. Nach jeder Phase: Tests, Doku-Update,
Freigabe → nächste Phase.

### Phase 1 — Analyse & Architektur (aktuell)
**Ziel:** Vollständige Doku-Basis, noch kein komplexer Code.

- [x] Repository analysiert (existierende Bauunternehmen-Website bleibt unangetastet)
- [x] Referenz-PDF `Roxel_alle_NVT_Einblasarbeiten_...02072026.pdf` gelesen (58 Seiten, 25 NVT, Regelpläne VZP-1/B I/2/B II/2/B I/15 als Zeichnungen enthalten)
- [x] `/docs/PROJECT_PLAN.md`
- [x] `/docs/ARCHITECTURE.md`
- [x] `/docs/DATA_MODEL.md`
- [x] `/docs/RULE_ENGINE.md`
- [x] `/docs/AI_PIPELINE.md`
- [x] `/docs/REVIEW_PROCESS.md`
- [x] `/docs/REFERENCE_CASES.md` (Tabelle 25 NVT aus PDF, mit Seitenzahl)

**Abnahme:** Nutzer liest die 6 Docs, gibt Phase 2 frei.

### Phase 2 — Datenmodell & Persistenz
**Ziel:** Domänenmodelle + Datenbank, testbar, ohne UI/Vision.

- Python-Projekt initialisieren (`pyproject.toml`, `uv`/`poetry`, `Makefile`, `.env.example`)
- Pydantic v2-Schemas für alle Entities aus `DATA_MODEL.md`
- SQLAlchemy 2 Mapping (SQLite dev, PostgreSQL prod)
- Alembic-Migrationen (initial)
- CRUD-Repositories pro Entity
- Unit-Tests für Schema-Validierung + CRUD

**Abnahme:** `pytest` grün, `alembic upgrade head` läuft, erstes `Project` + `NVT` per Skript anlegbar.

### Phase 3 — PDF-Analyse & Referenzfall-Extraktion
**Ziel:** Roxel-PDF strukturiert nach `/data/reference_cases/` extrahieren.

- `scripts/extract_reference_cases.py` mit PyMuPDF (fitz)
- Pro NVT: `nvt.json` + `photos/` + optional `lageplan.png`
- Regelplan-Zeichnungen S. 53–56 der PDF nach `/knowledge/regelplaene/{VZP1,B1_2,B2_2,B1_15}/plan.pdf` + `preview.png`
- **Metadaten-Felder bleiben leer** (`TODO`) — nur `id`, `name`, `quelle`, `source_page` werden befüllt, fachliche Inhalte kommen später vom Nutzer
- Regressionstest: 25 NVT-Ordner müssen entstehen, JSON valide

**Abnahme:** Extraktion reproduzierbar, `pytest tests/test_extraction.py` grün.

### Phase 4 — Upload, Foto-Import, OCR, NVT-Erkennung
**Ziel:** Ordner/ZIP hochladen, NVT-IDs erkennen, Adressen aus Foto-Overlay lesen.

- Upload-Endpoint (FastAPI): akzeptiert Ordner-Tree oder ZIP
- Beide Layout-Varianten aus Build-Prompt §11 (`NVT_7101.jpg` flach ODER `NVT_7101/01.jpg`)
- OCR-Interface (default Tesseract lokal, austauschbar), extrahiert NVT-Nummer, Straße, Hausnummer, PLZ, Ort, GPS, Datum
- NVT-Erkennung mit Prioritätskette: User → Dateiname → OCR → Vision
- Mehrere NVT auf einem Foto → `MANUELLE_PRÜFUNG_ERFORDERLICH`

**Abnahme:** Test-ZIP mit 5 NVT-Fotos ergibt 5 `NVT`-Records mit korrekter ID/Adresse.

### Phase 5 — Vision-Pipeline
**Ziel:** EnvironmentModel + WorkArea + TrafficModel aus Fotos.

- `VisionProvider`-Interface + `AnthropicVisionProvider` (Claude, Default)
- Prompts als Markdown in `/prompts/` (versioniert)
- Strenges JSON-Output-Schema (Pydantic) — keine Freitext-Antworten als Datenquelle
- Multi-Foto-Aggregation pro NVT
- Widersprüche → `MANUELLE_PRÜFUNG_ERFORDERLICH`
- Werte, die nicht zuverlässig aus dem Bild kommen: `UNKNOWN`, nicht Schätzwert

**Abnahme:** Referenzfall NVT 7107 wird analysiert → strukturiertes `EnvironmentAnalysis` mit erwarteten Flags (Gehweg=ja, Fahrbahn=ja, Radweg=nein).

### Phase 6 — Rule Engine
**Ziel:** Deterministische Regelplan-Auswahl aus `EnvironmentAnalysis` + Regelplan-Bibliothek.

- Prädikat-Set (`has_sidewalk`, `is_cul_de_sac`, `intersection_present`, …)
- Kandidatensuche über `metadata.json` der Regelpläne
- Ausschlusskriterien-Prüfung
- Confidence-Trennung: `vision_confidence`, `rule_confidence`, `data_completeness`
- Statuscodes: `AUTO_FREIGABE_VORBEREITET`, `AUTO_VORSCHLAG`, `MANUELLE_PRÜFUNG_ERFORDERLICH`, `NICHT_BEURTEILBAR`, `REGELPLAN_NICHT_GEFUNDEN`, `WIDERSPRUCH_ZWISCHEN_QUELLEN`
- **Keine hardcoded Rechtsregeln ohne `source_document`-Referenz**

**Abnahme:** Für die 25 Referenzfälle keine falschen Freigaben; Privatflächen-Fälle (7109/7113/7114) landen im Sonderpfad; Sackgassen-Fall (7103) triggert Warnung.

### Phase 7 — Review-UI (Human-in-the-Loop)
**Ziel:** Web-UI (React+TS+Vite) für Prüfung/Korrektur/Freigabe.

- Dashboard mit Projekt-Übersicht + Statusverteilung
- NVT-Prüfseite (Foto | Karte/Visualisierung | Analyse/Regelplan/Warnungen)
- Buttons: Freigeben, Ändern, Manuell, Analyse korrigieren, Neu analysieren
- Editierbar: NVT-ID, Adresse, GPS, Arbeitsbereich, Bulli-Position, Verkehrsflächen, Regelplan, Absperrelemente, Kommentare
- Filter (NVT/Adresse/Regelplan/Status/manuelle Prüfung/…)
- Audit-Log-Einträge live sichtbar
- Freigabe nur wenn Status ≥ `APPROVED`

**Abnahme:** Ein NVT lässt sich Ende-zu-Ende freigeben; Rejection triggert kein Export.

### Phase 8 — Absicherungsvisualisierung
**Ziel:** Absperrung auf Foto überlagern.

- Symbol-Set unter `/data/symbols/` (Warnbake, Leitbake, Absperrschranke, Absperrgitter, Verkehrszeichen — nur was in Regelplänen belegt ist)
- Overlay-Modell mit normalisierten 0–1-Koordinaten (auflösungsunabhängig)
- Originalfoto bleibt unverändert; `original.jpg`, `analysis.jpg`, `proposal.jpg`, `final.jpg`
- Editor: Baken verschieben, Absperrverlauf ändern
- **Nur Sicherungselemente, die im ausgewählten Regelplan vorgesehen sind**

**Abnahme:** Für NVT 7107 entsteht ein `proposal.jpg` mit Leitbaken an plausiblen Positionen.

### Phase 9 — Word-Export
**Ziel:** Produktionstaugliche Anlage zur VRA.

- Aufbau nach Master-Prompt §16 / Build-Prompt §35: Deckblatt, Übersichtstabelle, Pro-NVT-Abschnitt
- QA-Gate vor Export (Prüfliste aus §26 Master-Prompt / §52 Build-Prompt)
- Zusatz-Report `analysis_report.html` (intern, mit Trace/Confidence/Audit — **niemals** im finalen Word)
- Optional: DOCX → PDF (Word bleibt Primärdokument)
- **Kein** behördliches Anschreiben, **kein** LLM-Prompt, **kein** Confidence-Wert im finalen Dokument

**Abnahme:** Export für Testprojekt mit 5 NVT erzeugt `VRA_NVT_Gesamt_YYYY-MM-DD.docx`, jede Seite plausibel.

### Phase 10 — Batch-Verarbeitung
**Ziel:** 20–500 NVT in einem Projekt zuverlässig durchlaufen.

- Job-Queue (SQLAlchemy-backed oder RQ+Redis)
- Rate-Limiting für Vision-Provider
- Retry mit exponential backoff
- Fehlerbudget pro NVT (nach N Fehlversuchen → manuelle Prüfung)
- Fortschritts-UI (Server-Sent-Events oder Polling)

**Abnahme:** 50 Testfotos laufen in < 15 min durch, keine hängenden Jobs.

### Phase 11 — Regressionstests
**Ziel:** Änderungen am System dürfen bestehende Referenzentscheidungen nicht stillschweigend ändern.

- Alle 25 Referenzfälle als `pytest`-Fixtures
- Erwartete Ausgabe = eingefrorenes JSON pro Referenzfall
- Änderungsdiff → CI-Warnung `Regression detected: NVT_7107 status changed …`
- Manuelle Bestätigung erforderlich, um Baseline zu aktualisieren

**Abnahme:** CI läuft grün; künstliche Änderung an Rule Engine löst Regression-Warnung aus.

### Phase 12 — Produktionshärtung
**Ziel:** Deploy-fähig.

- `docker-compose.yml` (backend / frontend / db / optional worker)
- ENV-Variablen dokumentiert, Secrets nur via ENV/Vault
- Backup-Strategie für DB + `/data/`
- Fehler-Logging (strukturiert, ohne PII)
- DSGVO-Check (Fotos = personenbezogene Daten, keine Weitergabe an externe Provider ohne Opt-in)
- Bedienungsanleitung (`README.md`) fertig

**Abnahme:** Frischer Deploy auf leerer Maschine klappt, Testprojekt läuft End-to-End.

---

## 5. Teststrategie (phasenübergreifend)

| Test-Ebene           | Was                                                            | Wo                            |
| -------------------- | -------------------------------------------------------------- | ----------------------------- |
| Unit                 | Prädikate, Schema-Validierung, CRUD                            | `tests/unit/`                 |
| Rule-Engine          | Deterministische Regel-Auswahl mit Fixture-Environments        | `tests/rules/`                |
| Vision-Contract      | Mock-Provider, Pydantic-Validierung, Halluzinations-Detektion  | `tests/vision/`               |
| Integration          | Upload → Extract → Analyze → Rule → Export                     | `tests/integration/`          |
| Regression           | 25 Referenzfälle vs. eingefrorene Baseline                     | `tests/regression/`           |
| Doc-Test             | DOCX-Struktur, keine leeren Platzhalter, keine Debug-Infos     | `tests/documents/`            |

## 6. Verantwortlichkeiten der Software vs. Nutzer

**Software:**
- Fotos + Standorte → strukturierte Analyse
- Regelplan-Kandidaten aus Bibliothek vorschlagen
- Visualisierung erzeugen
- Word-Anlage generieren
- Alles protokollieren

**Nutzer / Fachanwender:**
- Regelplan-`metadata.json` befüllen (`voraussetzungen`, `ausschlusskriterien`, `source_document`, …)
- RSA-21-Ausschnitte / lokale Vorgaben in `/knowledge/` einpflegen
- Jede Freigabe fachlich prüfen
- Behördliches Anschreiben separat erstellen

**Behörde:**
- Prüfung, Genehmigung, Anschreiben

## 7. Nicht-Ziele (bewusst raus)

- Kein automatischer PDF-Versand an Behörde
- Kein Rechtsberatungs-Chatbot
- Keine Auto-Freigabe ohne menschliche Bestätigung
- Kein Nachbau des behördlichen Anschreibens
- Keine Regelinhalte aus dem Modell-Gedächtnis; nur eingespeiste Quellen

## 8. Umgang mit fehlenden Eingaben

Wenn RSA-21 / lokale Vorgaben / weitere Regelpläne fehlen:

- Strukturen bleiben (Ordner + Platzhalter-README)
- System zeigt: `"Regelplanbibliothek unvollständig"`
- Keine Verwendung erfundener Regeln
- Prozess läuft, aber jeder betroffene NVT landet in manueller Prüfung
