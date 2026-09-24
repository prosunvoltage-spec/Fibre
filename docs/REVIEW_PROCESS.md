# REVIEW_PROCESS — VRA-NVT-Automation

> Prüfprozess, State-Machine, UI-Layout, Audit-Log, Freigabekriterien,
> QA-Gate vor Export.

---

## 1. Grundsatz

**Nichts wird ohne fachliche menschliche Freigabe exportiert.**
Auch `AUTO_FREIGABE_VORBEREITET` bedeutet: „grüne Ampel für den Reviewer“,
nicht „System hat freigegeben“. Erst ein expliziter Klick eines Users setzt
den Status auf `APPROVED`. Erst `APPROVED` ist exportfähig.

---

## 2. State-Machine je NVT

```
                  ┌───────┐  Upload registriert
                  │  NEW  │◄──────────────────────────────────────┐
                  └───┬───┘                                       │
                      │  Worker startet Analyse                   │
                      ▼                                           │
                ┌───────────┐                                     │
                │ ANALYZING │                                     │
                └─────┬─────┘                                     │
             success  │  ┌──error nach 3 Retries                  │
                      ▼  ▼                                        │
                ┌──────────────┐                                  │
                │  ANALYZED    │──► auto: Rule Engine ────┐       │
                └──────┬───────┘                          │       │
                       │            ┌─────────────────────┘       │
                       │            ▼                             │
                       │       Decision.code                      │
                       │   ┌───────┼─────────────────────┐        │
                       │   ▼       ▼                     ▼        │
             ┌───────────────┐  ┌──────────────┐  ┌─────────────┐ │
             │ NEEDS_REVIEW  │  │ NEEDS_REVIEW │  │NEEDS_REVIEW │ │
             │ (Vorschlag)   │  │(Manuelle Pf.)│  │(Widerspr.)  │ │
             └──────┬────────┘  └──────┬───────┘  └──────┬──────┘ │
                    │                  │                  │        │
        Reviewer ändert       Reviewer erledigt   Reviewer wählt   │
        Analyse/Regelplan     manuelle Prüfung   einen Kandidaten  │
                    └──────────────┬───┴───────────────────┘        │
                                   ▼                                │
                            ┌────────────┐                          │
                            │ REVIEWED   │  Zwischenstand           │
                            └──────┬─────┘                          │
                                   │  Reviewer klickt „Freigeben"   │
                                   ▼                                │
                     ┌─────────────────────────┐                    │
                     │        APPROVED         │                    │
                     └───┬─────────────────┬───┘                    │
              QA-Gate ok │                 │ QA-Gate fail           │
                         ▼                 └────► NEEDS_REVIEW ─────┘
                    ┌──────────┐
                    │ EXPORTED │
                    └──────────┘

REJECTED kann jederzeit ab NEEDS_REVIEW gesetzt werden (Reviewer verwirft NVT).
```

**Erlaubte Übergänge** (in `app/core/services/nvt_service.py::TRANSITIONS`):

| Von             | Nach                                      |
| --------------- | ----------------------------------------- |
| NEW             | ANALYZING · REJECTED                      |
| ANALYZING       | ANALYZED · NEEDS_REVIEW · REJECTED        |
| ANALYZED        | NEEDS_REVIEW · REVIEWED (nur bei AUTO_FREIGABE_VORBEREITET) |
| NEEDS_REVIEW    | REVIEWED · REJECTED · ANALYZING (re-run)  |
| REVIEWED        | APPROVED · NEEDS_REVIEW · REJECTED        |
| APPROVED        | EXPORTED · NEEDS_REVIEW (bei nachträglicher Änderung) |
| EXPORTED        | (keine Rück-Übergänge; neuer Export = neue Version) |
| REJECTED        | (Endzustand; kann via UI reaktiviert → NEEDS_REVIEW) |

Ungültige Übergänge werfen `InvalidStateTransition` und werden im AuditLog
festgehalten.

---

## 3. Wer setzt welchen Status?

- **NEW → ANALYZING**: System (Worker)
- **ANALYZING → ANALYZED**: System (Vision fertig)
- **ANALYZED → NEEDS_REVIEW / REVIEWED**: System (Rule Engine)
- **NEEDS_REVIEW → REVIEWED**: **Mensch** (Reviewer)
- **REVIEWED → APPROVED**: **Mensch** (Reviewer, expliziter Klick)
- **APPROVED → EXPORTED**: System (Export-Job)
- **irgendein State → REJECTED**: Mensch

**Vier-Augen-Prinzip** (optional, per Projekt-Setting):
Wenn `project.require_second_review = true`, muss ein zweiter Reviewer
`APPROVED` bestätigen (Statuszwischenschritt `SECOND_REVIEW_PENDING`, nicht in
der obigen Basis-Machine — additive Migration in Phase 12).

---

## 4. Review-UI-Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Projekt:  Roxel Einblasarbeiten 2026    NVT 7107 / 25    [◀ prev] [next ▶]│
├────────────────────────┬─────────────────────┬───────────────────────────┤
│                        │                     │  ANALYSE                  │
│                        │                     │  road_present     ✓       │
│                        │                     │  sidewalk_present ✓       │
│    [Originalfoto]      │  [Karte/Overlay]    │  cycleway         ✗       │
│    [zoombar]           │  Bulli · Absperr-   │  intersection     ✗       │
│                        │  fläche · Baken     │  cul_de_sac       ✗       │
│                        │  editierbar         │                           │
│                        │                     │  REGELPLAN                │
│    ┌── Foto-Tabs ──┐   │                     │  ▸ B1/2 (Vorschlag)       │
│    │ Foto 1 · 2·3  │   │                     │    Alternative: B2/2      │
│    └───────────────┘   │                     │                           │
│                        │                     │  BEGRÜNDUNG               │
│  Adresse: Roxeler…579  │                     │  Wohnstraße, NVT im       │
│  GPS:    51.94, 7.53   │                     │  Seitenbereich, Fußverkehr│
│  NVT-ID: 7107          │                     │  über gegenüber. Gehweg…  │
│                        │                     │                           │
│  Confidence:           │                     │  WARNUNGEN                │
│  Vision  0.91          │                     │  —                        │
│  Rule    0.85          │                     │                           │
│  Data    0.88          │                     │  QUELLEN (Klick öffnet)   │
│                        │                     │  · RSA21 Teil D           │
│                        │                     │  · Auflagen Stadt Münster │
│                        │                     │                           │
├────────────────────────┴─────────────────────┴───────────────────────────┤
│  [ ✓ Freigeben ]  [ Regelplan ändern ]  [ Arbeitsbereich bearbeiten ]   │
│  [ Absperrung bearbeiten ]  [ Analyse korrigieren ]  [ Neu analysieren ]│
│  [ ⚠ Manuelle Prüfung ]     [ ✗ Ablehnen ]     [ Kommentar hinzufügen ] │
├──────────────────────────────────────────────────────────────────────────┤
│  AUDIT (letzte 5 Ereignisse)                                             │
│  · 15:42 Nico N.   ENVIRONMENT_EDITED  (setzt cul_de_sac: unknown→no)   │
│  · 15:41 System    DECISION_CREATED    (B1/2, AUTO_VORSCHLAG)           │
│  · 15:40 System    VISION_ANALYZED     (confidence 0.91)                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Frontend-Route:** `/projects/:pid/nvts/:nid`

**Wichtige UX-Details:**
- Freigabe-Button ist **erst aktiv**, wenn:
  - `Decision` vorhanden
  - Kein `WARNING` mit Prio ≥ HIGH offen
  - Bei `MANUELLE_PRUEFUNG`: Reviewer muss Regelplan explizit gewählt haben
  - Kein `contradiction` offen
- Regelplan-Ändern-Dialog zeigt **alle** Regelpläne der Bibliothek, aber:
  - Kandidaten der Rule Engine oben, grün markiert
  - Nicht-Kandidaten unten, grau, mit Warnung „nicht durch Rule Engine bestätigt“
- Ändert der Reviewer den Regelplan, muss er einen **Kommentar** eingeben
  (min. 10 Zeichen) — dieser landet im AuditLog

---

## 5. Filter im Dashboard

Aus Build-Prompt §39:

- NVT-Nummer
- Adresse (Volltext)
- Regelplan (Multiselect)
- Status (Multiselect)
- Nur manuelle Prüfung
- Nur Privatfläche
- Betroffene Fläche: Gehweg / Radweg / Fahrbahn / Kreuzung / Bushaltestelle
- Projekt

Sortier-Optionen: nach Status, nach Priorität (Warnungen zählen), alphabetisch.

Zusätzlich: **„Nur meine offenen"** — filtert auf NVT, für die der eingeloggte
User als letzter etwas geändert oder als „to-do“ markiert hat (Phase 11).

---

## 6. Audit-Log

Jede Aktion — System oder Mensch — landet als `AuditLog`-Eintrag. Doppelt:
DB + `data/audit.jsonl` (append-only, Backup).

**Event-Katalog** (`app/audit/events.py`):

| Event                       | Beschreibung |
| --------------------------- | ------------ |
| PROJECT_CREATED             | |
| UPLOAD_RECEIVED             | |
| PHOTO_EXTRACTED             | Datei aus Upload extrahiert |
| NVT_DETECTED                | NVT-ID aus Foto/Dateiname erkannt |
| NVT_MERGED                  | Fotos zu bestehendem NVT hinzugefügt |
| NVT_DUPLICATE_MARKED        | |
| OCR_COMPLETED               | |
| VISION_STARTED              | |
| VISION_COMPLETED            | mit vision_confidence |
| VISION_FAILED               | Retries erschöpft |
| RULE_ENGINE_DECIDED         | mit trace |
| DECISION_CREATED            | |
| ENVIRONMENT_EDITED          | Reviewer korrigiert Feld |
| WORKAREA_EDITED             | |
| RULEPLAN_CHANGED            | (old, new, comment) |
| VISUALIZATION_EDITED        | Overlay-Symbol verschoben |
| REVIEW_HOLD                 | Manuelle Prüfung angefordert |
| APPROVED                    | Freigabe |
| REJECTED                    | Ablehnung |
| EXPORT_STARTED              | |
| EXPORT_COMPLETED            | mit Dateiname |
| QA_GATE_PASSED / FAILED     | |
| RULESET_VERSION_CHANGED     | Regelwerks-Update (project-level) |

**Format eines Eintrags:**

```json
{
  "id": 4321,
  "timestamp": "2026-08-13T15:42:07.123456Z",
  "user": "nico.nessen",
  "project_id": "…",
  "nvt_id": "…",
  "action": "RULEPLAN_CHANGED",
  "old_value": "B1/2",
  "new_value": "B2/2",
  "ruleset_version": "v1",
  "model_id": "claude-…",
  "payload": {
    "comment": "Verkehrsstärke höher als vermutet, B2/2 sicherer",
    "trace_before_sha": "...",
    "trace_after_sha": "..."
  }
}
```

**Unveränderbarkeit:** DB-Constraint verbietet `UPDATE` auf `audit_log`.
Löschungen sind für Superuser möglich, aber selbst diese hinterlassen einen
`AUDIT_LOG_DELETED`-Eintrag.

---

## 7. QA-Gate (vor Export)

Läuft automatisch beim Klick auf „Export“ und blockiert, wenn eine Prüfung
fehlschlägt.

Prüfungen (aus Master-Prompt §26, Build-Prompt §52):

- [ ] Jeder NVT hat eine `nvt_number`
- [ ] Jeder NVT hat mindestens ein Foto
- [ ] Jeder NVT hat Adresse ODER GPS
- [ ] Jeder NVT hat `EnvironmentAnalysis`
- [ ] Jeder NVT hat `Decision` mit `selected_ruleplan` ODER `PRIVATFLAECHE`
- [ ] Jeder NVT hat mindestens einen Review-Eintrag `APPROVED`
- [ ] Kein NVT-Nummer-Duplikat innerhalb des Projekts
- [ ] Alle referenzierten Regelpläne existieren und sind `is_complete=True`
- [ ] Kein NVT hat offene `HIGH`-Warnungen
- [ ] Visualisierung vorhanden (`Visualization.rendered_photo_id` gesetzt oder
      Regelplan = PRIVATFLAECHE)
- [ ] Kein Foto ist als `analysis` / `proposal` mit dem Original verwechselt

Ergebnis wird als `qa_gate_report`-JSON in `Export` gespeichert. Fehlerhafte
Prüfungen erzeugen eine Fehlermeldung mit Direktlink pro betroffenem NVT.

---

## 8. Export-Regeln

Der finale Word-Export darf **nur** enthalten:

- NVT-Nummer, Adresse, GPS (falls vorhanden)
- Originalfoto + Absicherungsdarstellung
- Regelplan-Abbildung + Regelplan-ID
- Fachlich formulierte Verkehrssituation
- Fachlich formulierte Absperrbegründung
- Prüfstatus („freigegeben“)

**Explizit verboten** im Export:

- LLM-Rohantwort
- Prompt-Text
- Confidence-Werte
- Modell-Metadaten
- Debug-Informationen
- Interne Kommentare (können mit Flag `visible_in_export=false` markiert werden)
- Ausschnitte aus Trace

Zusätzlich wird `analysis_report.html` (intern, alles Genannte) neben dem
Word gespeichert. Beide Dateien tragen dieselbe `export_id`.

---

## 9. Nachträgliche Änderungen

Wenn nach `EXPORTED` etwas geändert wird (z.B. Reviewer erkennt Fehler):

1. NVT-Status springt zurück auf `NEEDS_REVIEW`
2. Bestehender `Export` wird als `superseded=true` markiert (nicht gelöscht)
3. Erneute Freigabe erzeugt neue `Export`-Version (v2 …)
4. AuditLog verknüpft alte + neue Version

**Regelwerks-Update** (`ruleset_version v1 → v2`):
- Alte Exports bleiben unberührt (`ruleset_version` in Decision eingefroren)
- Neue Analysen laufen mit v2
- UI zeigt Warnung „NVT mit älterer Regelwerks-Version, ggf. neu prüfen“

---

## 10. Konservative Grundhaltung

Wenn ein Reviewer unsicher ist, ist der richtige Weg:

1. **„Manuelle Prüfung"** klicken (Status bleibt `NEEDS_REVIEW`)
2. Kommentar eintragen
3. Fachanwender / Bauleiter konsultieren
4. Erst dann freigeben oder ablehnen

Es gibt bewusst **keinen** Sammel-Freigabe-Button („alle 25 auf einmal
freigeben"). Freigaben sind pro NVT und pro Klick.

Der Batch-Freigabe-Wunsch für Trivialfälle (z.B. Privatflächen) kann in
Phase 12 als Sonder-UI ergänzt werden, aber immer mit expliziter Bestätigung
und AuditLog-Einträgen pro NVT.
