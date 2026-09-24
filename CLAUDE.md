# CLAUDE.md — VRA-NVT-Automation

Diese Datei enthält dauerhafte Projektregeln für jede Claude-Code-Session
in diesem Repository. Sie gilt zusätzlich zu, nicht anstelle von,
`docs/PROJECT_PLAN.md`, `docs/ARCHITECTURE.md` und `docs/CURRENT_STATE.md`.

## Was dieses Projekt ist

Ein Fachsystem, das aus NVT-Fotos (Netzverteilerschränke, Glasfaser-
Einblasarbeiten) die **technische Anlage** zu einer verkehrsrechtlichen
Anordnung (VRA) erzeugt: Foto → KI-gestützte Umgebungsanalyse →
deterministische Regelplan-Auswahl → Absicherungs-Visualisierung →
menschliche Freigabe → Word-Dokument.

**Zwei völlig getrennte Projekte leben in diesem Repo:**
1. Statische Bauunternehmen-Website (`index.html`, `css/`, `js/`, `img/`,
   `referenzen.html`, `ueber-uns.html`, `kontakt.html`, `impressum.html`,
   `datenschutz.html`) — **nicht anfassen**, außer explizit dazu
   aufgefordert. Gehört zu einem anderen Branch/Kontext
   (`claude/construction-website-set3zs`).
2. Das VRA-NVT-System (`app/`, `docs/`, `knowledge/`, `data/`, `prompts/`,
   `scripts/`, `tests/`, `alembic/`) — das eigentliche Arbeitsprojekt.

Branch für alle VRA-Arbeit: `claude/vra-glasfaser-automation-mgnehz`.

## Nicht verhandelbare fachliche Regeln

Diese Regeln stammen aus dem ursprünglichen Auftrag und sind **hart**,
nicht Stil-Empfehlungen:

1. **Niemals Regelplan-Inhalte erfinden.** Die fachliche Bedeutung eines
   Regelplans (`geeignet_fuer`, `voraussetzungen`, `ausschlusskriterien`)
   kommt ausschließlich aus `knowledge/regelplaene/*/metadata.json`,
   gepflegt vom Fachanwender. Claude darf diese Felder nicht selbst mit
   Fachinhalt befüllen — auch nicht "plausibel klingend".
2. **KI liefert Beobachtungen, nie Entscheidungen.** Vision-Modelle
   (`app/vision/`) beschreiben nur die Szene. Die Regelplan-Auswahl macht
   ausschließlich die deterministische Rule Engine (`app/rules/engine.py`
   — reine Funktion, kein LLM-Zugriff).
3. **Konservativ im Zweifel.** Wenn Daten unklar sind: `Ternary.UNKNOWN`
   statt Rateschluss, `MANUELLE_PRUEFUNG` statt Auto-Freigabe. Ein
   Regelplan mit `is_complete=False` darf **nie** zu
   `AUTO_FREIGABE_VORBEREITET` führen (siehe `app/rules/engine.py`).
4. **Menschliche Freigabe ist Pflicht.** Kein Status erreicht `APPROVED`
   ohne einen expliziten `Review`-Eintrag mit `action=APPROVED`. Das
   QA-Gate (`app/validation/qa_gate.py`) blockt den Export sonst.
5. **Das behördliche Anschreiben wird NICHT erzeugt.** Das System liefert
   nur die technische Anlage (Word-Dokument). Das Anschreiben erstellt die
   Straßenverkehrsbehörde selbst.
6. **Keine Debug-/Modell-Informationen im finalen Word.** Confidence-Werte,
   Prompt-Hashes, Modell-IDs, Rohantworten dürfen nur in den internen
   HTML-Bericht (`app/documents/html_report.py`), niemals ins Word
   (`app/documents/word_builder.py`). Bei Änderungen an beiden Dateien:
   per Test verifizieren (siehe `tests/test_export.py`,
   `test_word_export_contains_nvt_numbers` prüft explizit auf verbotene
   Begriffe).
7. **Originalfotos werden nie überschrieben.** Overlays/Visualisierungen
   entstehen als neue Datei (`*_proposal.jpg`), das Original bleibt
   unangetastet.
8. **Regelwerks-Versionierung.** Jede `Decision` friert ihre
   `ruleset_version` ein. Ändert sich später die Wissensbasis, dürfen
   alte, bereits exportierte Entscheidungen nicht rückwirkend verändert
   werden.

## Wie an diesem Projekt gearbeitet werden soll

- **Phasenweise vorgehen**, nicht alles auf einmal. Die Phasen-Roadmap
  steht in `docs/PROJECT_PLAN.md` §4. Nach jeder Phase: Tests grün →
  committen → pushen → auf Nutzer-Freigabe warten, bevor die nächste
  Phase beginnt (siehe `docs/PROJECT_PLAN.md` "Wichtige Entwicklungsregel").
- **Sprache:** Antworten, Commit-Messages, Code-Kommentare und
  Dokumentation durchgehend auf Deutsch (Nutzer-Vorgabe).
- **Tests vor Commit.** `make test` muss grün sein. Aktueller Stand siehe
  `docs/CURRENT_STATE.md`.
- **Migrations:** Neue SQLAlchemy-Modelländerungen brauchen eine Alembic-
  Revision (`make revision M="..."`). Das `script.py.mako`-Template
  importiert `app.core.types` automatisch (wegen des custom `GUID`-Typs).
- **Wissensbasis (`knowledge/`) enthält keine Binärdateien im Git.**
  `.gitignore` schließt `*.pdf`, `*.png`, `*.jpg` etc. unter `knowledge/`
  aus. Nur `*.json`/`*.md`-Metadaten werden getrackt. Binaries entstehen
  reproduzierbar über `scripts/extract_reference_cases.py` aus der
  Referenz-PDF (liegt nicht im Repo, sondern im Upload-Verzeichnis der
  Session — Pfad siehe `docs/CURRENT_STATE.md`).
- **Demo-/Testdaten niemals in die echte Wissensbasis schreiben.** Für
  Vorführzwecke (z.B. "wie sieht das Word aus") eine separate, klar als
  DEMO markierte Regelplan-Bibliothek an einem Temp-Pfad verwenden —
  siehe Vorgehen in `docs/CURRENT_STATE.md` unter "E2E-Demo-Skript".
- **Keine ungefragten Refactorings.** Funktionierender Code wird nicht
  umgeschrieben, nur weil er "eleganter" ginge. Neue Anforderungen additiv
  umsetzen.

## Technischer Kontext (Kurzfassung — Details in docs/ARCHITECTURE.md)

- **Backend:** Python 3.11, FastAPI, Pydantic v2 (`extra="forbid"`
  überall als Anti-Halluzinations-Schutz), SQLAlchemy 2, Alembic, SQLite
  (dev) / PostgreSQL (prod-fähig, ungetestet).
- **KI:** Anthropic Claude via `app/vision/anthropic_provider.py`
  (braucht `ANTHROPIC_API_KEY`), Mock-Provider für Tests/Offline-Betrieb.
- **OCR:** Tesseract (`tesseract-ocr`, `tesseract-ocr-deu` — System-Paket,
  bereits installiert in dieser Umgebung, ggf. in neuer Umgebung
  nachinstallieren).
- **Dokumente:** `python-docx` (Word), eigener HTML-Report (kein
  externes PDF-Toolkit).
- **Bilder:** Pillow für Overlay-Rendering, PyMuPDF (`pymupdf`) für
  PDF-Extraktion.
- **Frontend:** noch nicht begonnen (Phase 7, React+TS+Vite geplant,
  siehe `docs/CURRENT_STATE.md`).

## Wo was steht

| Frage | Antwort |
|---|---|
| Was ist als Nächstes geplant? | `docs/CURRENT_STATE.md` → "Nächste Schritte" |
| Wie ist die Architektur aufgebaut? | `docs/ARCHITECTURE.md` |
| Welche Phase macht was? | `docs/PROJECT_PLAN.md` §4 |
| Wie funktioniert die Rule Engine? | `docs/RULE_ENGINE.md` |
| Wie funktioniert die Vision-Pipeline? | `docs/AI_PIPELINE.md` |
| Wie läuft der Freigabe-Prozess? | `docs/REVIEW_PROCESS.md` |
| Welche Datenfelder gibt es? | `docs/DATA_MODEL.md` |
| Was steht in der Referenz-PDF? | `docs/REFERENCE_CASES.md` |
