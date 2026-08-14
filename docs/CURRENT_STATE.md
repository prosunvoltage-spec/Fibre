# CURRENT_STATE — VRA-NVT-Automation

> Exakter Projektstand für den Wiedereinstieg in einer neuen Claude-Code-
> Session. Erstellt am 14.08.2026. Letzter Commit: `a1357bb` ("Phase 8+9:
> Absicherungs-Visualisierung + Word-Export"), gepusht auf
> `claude/vra-glasfaser-automation-mgnehz`.

---

## 1. Was ist fertig (Phasen 1–9 von 12)

| Phase | Inhalt | Status | Commit |
|---|---|---|---|
| 1 | Doku (7 Dateien in `docs/`) | ✅ | `3a67e9f` |
| 2 | Datenmodell, SQLAlchemy 2, Alembic | ✅ | `c57321b` |
| 3 | Regelplan-/Referenzfall-Bibliothek, PDF-Extraktion | ✅ | `16c4197` |
| 4 | Upload, OCR, NVT-Erkennung, FastAPI-Grundgerüst | ✅ | `906eba3` |
| 5 | Vision-Pipeline (Claude+Mock, Prompts, Halluzinations-Schutz) | ✅ | `cc8d711` |
| 6 | Deterministische Rule Engine | ✅ | `b7ef252` |
| 7 | Review-UI (React/TS/Vite) | ⏳ **nicht begonnen** | — |
| 8 | Absicherungs-Visualisierung (Overlay auf Foto) | ✅ | `a1357bb` |
| 9 | Word-Export + interner HTML-Bericht | ✅ | `a1357bb` |
| 10 | Batch-Verarbeitung (Queue, 20–500 NVT) | ⏳ nicht begonnen | — |
| 11 | Regressions-Baseline einfrieren (CI-Gate) | ⏳ teilweise* | — |
| 12 | Produktionshärtung (Docker, Backup, DSGVO-Check) | ⏳ nicht begonnen | — |

\* `tests/test_regression_reference_cases.py` existiert bereits (aus
Phase 6) und läuft gegen die 26 Referenzfälle, aber es gibt noch keine
eingefrorene Baseline mit Diff-Warnung bei Abweichung — nur Property-
Assertions (Privatfläche→PRIVATFLAECHE etc.).

**Phase 7 wurde bewusst übersprungen** — auf Wunsch des Nutzers kam
Phase 8+9 zuerst, damit ein greifbares Ergebnis (Word-Datei) vor dem
aufwendigeren Frontend steht.

---

## 2. Testsuite

```bash
make test
# 191 passed, 1 warning in ~2.5s
```

24 Testdateien unter `tests/`, keine Unit/Integration-Unterordner (flache
Struktur, abweichend vom ursprünglichen Phase-1-Plan). Testet: Enums,
Pydantic-Schemas, ORM-Modelle, Repositories (State-Machine-Guard), OCR-
Parser, NVT-Detector, Upload-Pipeline, API-Endpoints, Vision-Schema/
Prompts/Pipeline/Aggregator, Environment-Builder, Predicates, Rule Engine,
Decision-Builder, Regression gegen 26 Referenzfälle, Visualisierung
(Symbols/Renderer/Proposer), QA-Gate, Word-/HTML-Export.

**Bekannte Ungenauigkeit:** Der Commit-Message-Text zu `a1357bb` behauptet
fälschlich "191 → 226 grün, davon 35 neu". Die tatsächliche Zahl war und
ist **191 Tests total, davon 18 neu in diesem Commit** (7 in
`test_visualization.py`, 5 in `test_qa_gate.py`, 6 in `test_export.py`).
Reiner Dokumentationsfehler im Commit-Text, kein Funktionsproblem — nicht
korrigiert (Commit ist bereits gepusht, kein Grund für History-Rewrite).

**Wiederkehrender Testfallstrick, falls neue Tests geschrieben werden:**
Die DB-Session läuft mit `expire_on_commit=False`. Wenn man ein Kind-
Objekt per `session.delete(obj)` löscht, ohne es vorher aus der
Python-seitigen Collection des Parents zu entfernen (z.B.
`nvt.photos.remove(photo)` vor `session.delete(photo)`), bleibt es in
`nvt.photos` im Speicher sichtbar, obwohl es in der DB weg ist. Das hat in
dieser Session bereits 4 Tests fehlschlagen lassen (siehe Git-History um
`a1357bb`). Immer erst aus der Collection entfernen, dann `session.delete`.

---

## 3. Was funktioniert End-to-End (verifiziert)

Kompletter Durchlauf wurde in dieser Session gegen 5 echte Fotos aus der
Referenz-VRA getestet:

```
Upload (ZIP, 5 Fotos NVT 7107/7109/7103/7124/7116)
  → Analyze (Mock-Vision mit realistischen Antworten)
  → Decide (Rule Engine mit Demo-Regelplan-Bibliothek, siehe §5)
  → Visualize (Overlay-Rendering)
  → Freigabe (simuliert per Direct-DB-Write, kein API-Endpoint dafür)
  → Export (QA-Gate → Word 10 MB + HTML-Report)
```

Ergebnis: valides Word-Dokument mit Deckblatt, Übersichtstabelle, 5 NVT-
Abschnitten (Original-Foto, Absicherungs-Darstellung, Regelplan-Abbildung,
fachlich formulierte Begründung). Verifiziert per Test, dass **keine**
Confidence-Werte/Modell-IDs/Prompt-Hashes im Word landen.

Die dabei erzeugten Artefakte (Demo-Regelplan-Bibliothek, Demo-Word,
Demo-Projekt in der DB) liegen **nicht im Repo**, sondern in der
Session-Scratchpad-Umgebung — siehe §5 für Details, falls der Lauf
wiederholt werden soll.

---

## 4. Kritischer offener Punkt: Regelplan-Metadaten sind fachlich leer

`knowledge/regelplaene/{VZP1,B1_2,B2_2,B1_15}/metadata.json` existieren,
aber die fachlichen Felder (`geeignet_fuer`, `voraussetzungen`,
`ausschlusskriterien`, `verkehrsraum`, `allowed_symbols`) sind **absichtlich
leer**. Das ist kein Bug — der Master-Prompt verbietet ausdrücklich, dass
Claude diese Inhalte erfindet.

**Konsequenz für den aktuellen Live-Zustand:** Wenn man jetzt (ohne
weitere Änderungen) einen echten NVT durch `POST .../decide` schickt,
kommt für alles außer Privatflächen-Fällen `REGELPLAN_NICHT_GEFUNDEN`
heraus — die Rule Engine funktioniert korrekt, hat aber nichts zum
Zuordnen.

**Nächster Schritt, den nur der Fachanwender (nicht Claude) machen kann:**
Diese 4 Dateien mit echten RSA-21-Inhalten befüllen. Format-Beispiel siehe
`knowledge/regelplaene/README.md` oder die Demo-Metadaten in §5 unten
(als Strukturbeispiel, NICHT als fachlich geprüfter Inhalt verwenden!).

---

## 5. E2E-Demo-Skript (Vorgehen zum Reproduzieren)

Für die Layout-Vorschau des Word-Dokuments wurde eine **separate, klar
als DEMO markierte** Regelplan-Bibliothek verwendet, um zu zeigen, wie das
System mit echten Fachdaten aussähe — ohne die reale (bewusst leere)
`knowledge/regelplaene/` anzufassen.

Das Demo-Skript lag unter (Session-Scratchpad, nicht im Repo, ggf. in
neuer Session nicht mehr vorhanden):
```
/tmp/claude-0/-home-user-Fibre/d9e3fd37-3923-50ea-9834-fe63e445f86e/
  scratchpad/build_demo_export.py
```

**Vorgehen, falls erneut eine Demo mit "echt aussehenden" Regelplan-Daten
gebraucht wird:**
1. Temp-Ordner mit `regelplaene/{B1_2,B2_2,VZP1,B1_15}/metadata.json`
   anlegen, `geeignet_fuer`/`voraussetzungen`/`allowed_symbols` mit
   Test-Prädikaten aus `app/rules/predicates.py::PREDICATE_REGISTRY`
   füllen (z.B. `is_residential_street`, `has_sidewalk`, `is_curve`,
   `is_cul_de_sac`, `is_main_road`).
2. `settings.knowledge_path` zur Laufzeit auf diesen Temp-Ordner
   umbiegen (`get_settings().knowledge_path = temp_path`) — **nie** die
   echte `knowledge_path` im Repo verändern.
3. `MockVisionProvider` mit realistischen `responses`-Dict pro
   Foto-Dateiname füttern (siehe `app/vision/mock_provider.py`).
4. Über die echten API-Endpoints laufen lassen (`TestClient(app)` aus
   `fastapi.testclient`), nicht die Services direkt aufrufen — testet so
   den echten Pfad.
5. Freigabe fehlt als Endpoint (siehe §6) — Workaround: direkt per
   `NvtRepo.update_status()` + `Review`-Row in einer `session_scope()`.
6. Alle erzeugten Artefakte (Demo-Projekt in `data/dev.db`, Demo-Exports
   in `data/projects/`) sind über `.gitignore` ausgeschlossen und wurden
   nicht committet.

---

## 6. Nächste Schritte (Vorschläge, keine Festlegung)

In Prioritätsreihenfolge, wie sie am Ende der letzten Session mit dem
Nutzer besprochen wurde:

1. **Fachanwender pflegt Regelplan-Metadaten** (§4) — blockiert nichts
   technisch, ist aber Voraussetzung dafür, dass die Rule Engine in der
   Praxis nützliche Vorschläge macht statt durchgehend
   `REGELPLAN_NICHT_GEFUNDEN`.
2. **Phase 10 (Batch-Verarbeitung)** — aktuell synchron, ein Projekt mit
   100 NVT würde 100 serielle Vision-API-Calls in einem Request bedeuten.
   Braucht mindestens einen einfachen Job-Queue-Mechanismus (SQLAlchemy-
   backed reicht laut ARCHITECTURE.md, kein Redis nötig).
3. **Phase 7 (Review-UI)** — der größte verbleibende Batzen. Ohne sie ist
   das System nur per `curl`/API bedienbar. Wichtig: Es fehlt aktuell noch
   ein **Freigabe-Endpoint** (`POST .../nvts/{id}/review` o.ä.) im Backend
   — der wurde bisher übersprungen, weil er eigentlich zur UI gehört. Vor
   oder mit Phase 7 nachholen.
4. **Phase 11 abschließen** — Baseline für Regressionstests einfrieren.
5. **Phase 12** — Docker-Compose, Backup, DSGVO-Prüfung.

**Offene Entscheidung vom Nutzer, noch nicht beantwortet:**
- Ob Tesseract-Systempaket in einer neuen Umgebung automatisch über ein
  Setup-Skript installiert werden soll (aktuell manuell in dieser Session
  per `apt-get install tesseract-ocr tesseract-ocr-deu` erledigt).

---

## 7. Bekannte Lücken / nicht Bugs, aber bewusst unfertig

- **Kein Freigabe-Endpoint.** `ReviewAction.APPROVED` lässt sich nur per
  direktem DB-Zugriff erzeugen, nicht über die API. Muss vor/mit Phase 7
  kommen.
- **`app/geodata/` existiert nicht.** Keine Adress-Geokodierung. NVT ohne
  OCR/EXIF-GPS und ohne manuelle Adresse bleiben ohne Standort (QA-Gate
  blockt das dann korrekt).
- **`opposing_sidewalk_available`-Prädikat** ist in `RULE_ENGINE.md` als
  Beispiel erwähnt, aber **nie implementiert** worden — `PREDICATE_REGISTRY`
  in `app/rules/predicates.py` hat es nicht. Falls eine `metadata.json`
  dieses Prädikat referenziert, wird es als "nicht implementiert" in
  `unmet_requirements` geführt (kein Crash, aber auch kein Ergebnis).
- **Similarity-Search** (RULE_ENGINE.md §7, AI_PIPELINE.md §9) — nicht
  gebaut. `ReferenceCaseLibrary` kann nur exakt nach `nvt_number` oder
  `ruleplan_label` filtern, keine Ähnlichkeitsberechnung.
- **`app/documents/pdf_export.py`** aus dem ursprünglichen Architektur-
  Plan existiert nicht — nur Word, kein PDF.
- **Kein MIME-Check via `python-magic`** bei Uploads, nur Datei-Endung.
- **OpenCV ist installiert, aber ungenutzt** — keine Kalibrierung/
  Kantenerkennung implementiert.
- Nur **ein** Prompt existiert (`environment_analysis.md`). Die in
  AI_PIPELINE.md geplanten weiteren Prompts (`traffic_analysis.md`,
  `ruleplan_reasoning.md`, `visualization.md`, `document_generation.md`)
  wurden nicht gebraucht, weil Verkehrsteilnehmer-Bewertung,
  Absicherungs-Vorschlag und Word-Text bisher **deterministisch aus den
  DB-Daten** erzeugt werden, nicht per zusätzlichem LLM-Call. Das ist eine
  bewusste Vereinfachung gegenüber dem Ursprungsplan — funktioniert, ist
  aber nicht 1:1 das, was AI_PIPELINE.md beschreibt. Falls das stört,
  mit dem Nutzer klären, ob es so bleiben soll.

---

## 8. Umgebungs-Setup (für neue Session/Maschine)

```bash
cd /home/user/Fibre
cp .env.example .env          # ANTHROPIC_API_KEY optional (Mock funktioniert ohne)
apt-get install -y tesseract-ocr tesseract-ocr-deu   # falls nicht vorhanden
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/pytest                # 191 passed erwartet
.venv/bin/python scripts/generate_symbols.py   # falls data/symbols/ fehlt (ist aber im Git)
```

Referenz-PDF für neue Extraktionsläufe (`scripts/extract_reference_cases.py`)
lag in dieser Session unter:
```
/root/.claude/uploads/d9e3fd37-3923-50ea-9834-fe63e445f86e/
  ce660562-Roxel_alle_NVT_Einblasarbeiten_weiterer_Durchfu_hrungszeitraum_02072026.pdf
```
Dieser Pfad ist **session-gebunden** und existiert in einer neuen Session
nicht automatisch — die bereits extrahierten Fotos liegen aber dauerhaft
(nur lokal, nicht im Git) unter `knowledge/referenzfaelle/NVT_*/photo.png`,
solange dieselbe Arbeitsumgebung weiterverwendet wird. Bei komplett neuer
Maschine müsste der Nutzer die PDF erneut bereitstellen.

---

## 9. Wichtige Entscheidungen aus der Konversation (nicht im Code sichtbar)

- **Tech-Stack-Wahl** (Python/FastAPI/React/SQLite→PostgreSQL) wurde vom
  Nutzer per `AskUserQuestion` explizit bestätigt (Phase-1-Planung), nicht
  von Claude allein entschieden.
- **Alt-Website bleibt unangetastet** war eine explizite Nutzer-Antwort
  auf eine Rückfrage in Phase 1 (Option "Unangetastet lassen, VRA-App
  parallel unter /app anlegen").
- **Reihenfolge Phase 8+9 vor Phase 7** war eine Empfehlung von Claude
  ("Word-Export ohne UI ist bereits nutzbar"), die der Nutzer akzeptiert
  hat. Phase 7 ist also nicht vergessen, sondern bewusst zurückgestellt.
- **Modellname:** Diese Session lief unter `claude-opus-4-7`, wurde per
  `/model claude-sonnet-5` auf Sonnet 5 umgeschaltet. Für neue Sessions
  ist das irrelevant, aber falls Commit-Historie oder frühere Nachrichten
  nach Modellnamen fragen: beide kamen in dieser Session zum Einsatz.
- **Kein Kompromiss bei Anti-Halluzination**, auch nicht für Demo-Zwecke:
  Die Demo-Regelplan-Bibliothek (§5) wurde bewusst *außerhalb* des Repos
  gehalten, obwohl es einfacher gewesen wäre, sie direkt in
  `knowledge/regelplaene/` zu schreiben. Diese Trennung sollte in Zukunft
  genauso gehandhabt werden.
