# RULE_ENGINE — VRA-NVT-Automation

> Deterministische Regelplan-Auswahl aus strukturiertem Umgebungsprofil.
> Kein LLM in dieser Schicht — die Rule Engine ist eine **reine Funktion**:
> `decide(environment, work_area, ruleplan_library, geodata) → Decision`.

---

## 1. Grundsätze

1. **Determinismus.** Gleicher Input → gleicher Output. Keine Zufallswerte.
2. **Keine Netz-/DB-Aufrufe.** Reine Business-Logik, komplett per Unit-Test abdeckbar.
3. **Keine hardcoded Rechtsregeln ohne Quelle.**
   - Falsch: `if sidewalk_width < 1.5: warn(...)`
   - Richtig: Regel steht als `RequirementSchema` in `metadata.json` mit
     `source_document`, `source_reference`, `source_page`.
4. **Konservativ.** Bei fehlender oder unklarer Datenlage nicht raten →
   `MANUELLE_PRUEFUNG_ERFORDERLICH`.
5. **Trennung von Confidence-Werten:**
   `vision_confidence`, `rule_confidence`, `data_completeness` sind
   getrennte Größen. Eine hohe `vision_confidence` allein rechtfertigt
   niemals eine Auto-Freigabe.
6. **Nur eingelesene Regelpläne wählbar.** Regelpläne mit `is_complete=False`
   können vorgeschlagen werden, führen aber nicht zu `AUTO_VORSCHLAG` bzw.
   `AUTO_FREIGABE_VORBEREITET`.

---

## 2. Pipeline (Pseudocode)

```
def decide(env, work_area, ruleplans, geodata=None) -> Decision:

    # 0. Sofort-Ausschlüsse (Privatfläche, Betriebsgelände)
    if env.private_property == YES:
        return DecisionCode.PRIVATFLAECHE (no ruleplan)

    if env.business_property == YES and inside_perimeter(work_area):
        return DecisionCode.PRIVATFLAECHE (Sonderfall Stadtwerke)

    # 1. Datenvollständigkeit prüfen
    completeness = compute_completeness(env, work_area)
    if completeness < CRITICAL_COMPLETENESS_THRESHOLD:
        return DecisionCode.MANUELLE_PRUEFUNG (reason: "Datenlage unzureichend")

    # 2. Betroffene Verkehrsteilnehmer bestimmen (deterministisch aus env + work_area)
    affected_users = derive_traffic_users(env, work_area)

    # 3. Harte Warnungen aus Kontext (nicht Ausschluss, aber Aufschlag auf Review-Priorität)
    warnings = []
    if env.intersection_present == YES:  warnings.append("Kreuzung im Nahbereich")
    if env.junction_present == YES:      warnings.append("Einmündung im Nahbereich")
    if env.cul_de_sac == YES:            warnings.append("Sackgasse — Vollsperrung prüfen")
    if env.bus_stop_nearby == YES:       warnings.append("Bushaltestelle betroffen")
    if env.fire_access == YES:           warnings.append("Feuerwehrzufahrt betroffen")
    if env.sight_relations_affected==YES:warnings.append("Sichtbeziehungen beeinträchtigt")

    # 4. Kandidatensuche über Regelplan-Bibliothek
    candidates = candidate_search(env, work_area, affected_users, ruleplans)

    # 5. Voraussetzungen prüfen (pro Kandidat)
    for c in candidates:
        c.unmet_requirements = check_requirements(c.ruleplan, env, work_area)

    # 6. Ausschlusskriterien anwenden
    for c in candidates:
        c.triggered_exclusions = check_exclusions(c.ruleplan, env, work_area)

    # 7. Filter: nur Kandidaten ohne getriggerte Ausschlüsse
    surviving = [c for c in candidates if not c.triggered_exclusions]

    # 8. Ranking
    ranked = rank(surviving, env, work_area, affected_users)

    # 9. Auswahl-Entscheidung
    if len(ranked) == 0:
        return DecisionCode.REGELPLAN_NICHT_GEFUNDEN
    if len(ranked) > 1 and ranked[0].score - ranked[1].score < TIE_THRESHOLD:
        return DecisionCode.WIDERSPRUCH (top-2 vorschlagen)

    top = ranked[0]
    rule_confidence = compute_rule_confidence(top, env, work_area)

    # 10. Freigabe-Vorbereitung
    if (top.unmet_requirements
        or completeness < AUTO_APPROVE_COMPLETENESS
        or rule_confidence < AUTO_APPROVE_RULE_CONF
        or warnings
        or not top.ruleplan.is_complete):
        return DecisionCode.AUTO_VORSCHLAG  (Human-Review Pflicht)

    return DecisionCode.AUTO_FREIGABE_VORBEREITET  (nur Vorbereitung, nicht auto-freigeben!)
```

**Auch `AUTO_FREIGABE_VORBEREITET` bedeutet nicht, dass das System freigibt.**
Es bedeutet nur: die Rule Engine hat keine Warnungen und alle Voraussetzungen
sind erfüllt. Die Freigabe erfolgt **immer** durch einen Menschen (siehe
`REVIEW_PROCESS.md`).

---

## 3. Prädikate

Prädikate sind kleine, benannte Funktionen `env → bool` bzw. `env → Ternary`.
Sie sind das **Vokabular**, mit dem `metadata.json` maschinenlesbare Bedingungen
formulieren kann.

```python
# app/rules/predicates.py — Auszug

def has_sidewalk(env) -> Ternary: ...
def has_cycleway(env) -> Ternary: ...
def road_affected(env, wa) -> bool: ...
def sidewalk_affected(env, wa) -> bool: ...
def cycleway_affected(env, wa) -> bool: ...
def is_cul_de_sac(env) -> Ternary: ...
def is_main_road(env) -> Ternary: ...
def is_residential_street(env) -> Ternary: ...
def opposing_sidewalk_available(env) -> Ternary: ...
def remaining_roadway_ge(env, wa, min_m) -> Ternary: ...    # "≥ 3,00 m"
def remaining_sidewalk_ge(env, wa, min_m) -> Ternary: ...
def sight_triangle_ok(env) -> Ternary: ...
def emergency_route_maintained(env, wa) -> Ternary: ...
def intersection_area(env) -> Ternary: ...
```

**Neue Prädikate dürfen nur ergänzt werden, wenn eine Regel sie tatsächlich braucht.**
Kein Vorratshalten. Alle Prädikate haben Unit-Tests mit expliziten Ternary-Fällen.

`Ternary.UNKNOWN` in einem Prädikat, das für die Entscheidung nötig ist,
zwingt die Engine in `MANUELLE_PRUEFUNG`.

---

## 4. Kandidatensuche

`candidate_search(env, wa, users, ruleplans) → list[RulePlanCandidate]`

Jedes `RulePlan.metadata.json` enthält ein Feld `geeignet_fuer` mit einer Liste
strukturierter Bedingungen. Beispiel (Ausschnitt aus B1/2 könnte so aussehen —
die exakten Werte kommen aus dem Regelwerk, nicht aus dem LLM):

```json
{
  "id": "B1/2",
  "geeignet_fuer": [
    { "predicate": "road_affected", "value": true },
    { "predicate": "cycleway_affected", "value": false },
    { "predicate": "is_residential_street", "value": "yes" }
  ],
  "voraussetzungen": [
    { "condition": "Restfahrbahnbreite ≥ 3,00 m",
      "machine_predicate": "remaining_roadway_ge",
      "args": { "min_m": 3.0 },
      "source_document": "Auflagen Stadt Münster",
      "source_reference": "Standardauflage §3",
      "source_page": null }
  ],
  "ausschlusskriterien": [
    { "condition": "Kreuzung im Absperrbereich",
      "machine_predicate": "intersection_area",
      "source_document": "…",
      "source_reference": "…" }
  ]
}
```

Kandidat gilt als **matched**, wenn **alle** `geeignet_fuer`-Bedingungen erfüllt sind.

---

## 5. Ranking

Ranking nur unter überlebenden Kandidaten (ohne getriggerte Ausschlüsse).
Ranking-Kriterien in Reihenfolge:

1. **Anzahl erfüllter Voraussetzungen** (mehr = besser)
2. **Spezifität** (Plan mit engerer `geeignet_fuer` bevorzugen, keine
   Über-Absicherung)
3. **Ähnlichkeit zu Referenzfällen** (aus `/knowledge/referenzfaelle/`),
   NUR als Tiebreaker, nie als Hauptkriterium
4. **Alphabetisch** (stabile Sortierung)

`score` ist eine gewichtete Kombination, dokumentiert in `app/rules/ranking.py`.

Wenn `top1.score - top2.score < TIE_THRESHOLD` (z.B. 0.05) →
`DecisionCode.WIDERSPRUCH` und beide Kandidaten werden dem Reviewer angeboten.

---

## 6. Sofort-Ausschlüsse (harte No-Gos)

Diese werden **vor** der Kandidatensuche geprüft und beenden die Pipeline sofort:

| Bedingung                                                   | Ergebnis |
| ----------------------------------------------------------- | -------- |
| `env.private_property == YES`                               | `PRIVATFLAECHE` — keine öffentliche VRA nötig |
| `env.business_property == YES` und Arbeitsbereich innerhalb | `PRIVATFLAECHE` |
| Foto-Qualität ungenügend                                    | `NICHT_BEURTEILBAR` |
| Mehrere NVTs im selben Foto                                 | `MANUELLE_PRUEFUNG` |
| Vision-Provider liefert kein valides JSON (nach Retries)    | `MANUELLE_PRUEFUNG` |
| `data_completeness < CRITICAL_COMPLETENESS_THRESHOLD`       | `MANUELLE_PRUEFUNG` |
| Widersprüche zwischen Fotos eines NVT                       | `MANUELLE_PRUEFUNG` |
| Regelplan-Bibliothek leer                                   | `REGELPLAN_NICHT_GEFUNDEN` |

Diese Ausschlüsse haben Vorrang vor jeder anderen Logik.

---

## 7. Confidence-Modell

Drei getrennte Werte, alle 0..1:

- **`vision_confidence`** — vom Vision-Provider gemeldet
- **`data_completeness`** — 1 minus Anteil `UNKNOWN`-Felder in `EnvironmentAnalysis`
- **`rule_confidence`** — berechnet aus:
  - Anteil erfüllter Voraussetzungen
  - Abwesenheit von Warnungen
  - Score-Abstand zum zweitbesten Kandidaten
  - Regelplan-`is_complete`-Flag

Freigabelogik:

| vision_conf | rule_conf | completeness | Ergebnis |
| ----------- | --------- | ------------ | -------- |
| ≥ 0.8       | ≥ 0.9     | ≥ 0.9        | `AUTO_FREIGABE_VORBEREITET` (nur „Grün-Ampel“ für Reviewer) |
| ≥ 0.7       | ≥ 0.7     | ≥ 0.7        | `AUTO_VORSCHLAG` (Reviewer erwartet, Pflicht) |
| sonst       |           |              | `MANUELLE_PRUEFUNG` |

Schwellwerte sind **konfigurierbar** (`app/config.py`) und werden pro
Regelwerks-Version eingefroren.

---

## 8. Decision-Trace

Jede Entscheidung erzeugt einen menschenlesbaren Ableitungspfad, der im
internen Prüfbericht (nicht im finalen Word) landet. Beispiel:

```
NVT 7107 · Roxeler Straße 579

Umgebung:
- road_present            = yes
- sidewalk_present        = yes
- cycleway_present        = no
- intersection_present    = no
- private_property        = no
- nvt_position            = at_roadside
- remaining_roadway_width = 3.4 m (aus Vision, confidence 0.86)

Betroffene Verkehrsarten:
- pedestrians    (affected, proposed_route: gegenüberliegender Gehweg)
- motor_vehicles (affected, proposed_route: Fahrspur reduziert)

Kandidaten:
[1] B1/2   — geeignet_fuer erfüllt · voraussetzungen erfüllt · 0 ausschlüsse · score 0.87
[2] B2/2   — geeignet_fuer erfüllt · 1 voraussetzung unklar   · 0 ausschlüsse · score 0.71
[3] VZP1   — geeignet_fuer teilw.  · 0 voraussetzungen        · 0 ausschlüsse · score 0.42

Warnungen: —
Metadaten: ruleset_version=v1, ruleplan_revision=sha256:…, model=claude-…, prompt=sha256:…

Vorschlag: B1/2
vision_confidence = 0.91 · rule_confidence = 0.85 · data_completeness = 0.88
Status: AUTO_VORSCHLAG · human_review_required = true
```

Der Trace wird JSON in `Decision.trace_json` gespeichert und im HTML-Report
formatiert dargestellt.

---

## 9. Testbarkeit

**Unit-Tests** in `tests/rules/`:

- `test_predicates.py` — jedes Prädikat mit YES/NO/UNKNOWN
- `test_candidate_search.py` — je Regelplan mind. 3 Fixtures (matches, no-match, edge)
- `test_exclusions.py` — jede harte Ausschlussregel einmal getriggert
- `test_ranking.py` — Tiebreak-Verhalten
- `test_full_engine.py` — 25 Referenzfälle als Snapshot-Test

**Referenzfall-Regression** in `tests/regression/`:

- Baseline: `data/regression/baseline/NVT_71xx.json`
- Testlauf schreibt aktuelle Ergebnisse; Diff bricht CI (außer explizit
  aktualisiert via `pytest --update-baseline`)

---

## 10. Was die Rule Engine NICHT tut

- **Nicht** interpretieren, was ein Foto zeigt (das macht Vision)
- **Nicht** Adressen geokodieren (das macht Geodata)
- **Nicht** Regeln aus Textquellen extrahieren (das macht der Fachanwender beim Pflegen)
- **Nicht** Confidence in Wahrscheinlichkeit umrechnen
- **Nicht** Auto-Freigabe erteilen — das darf nur ein Mensch
- **Nicht** Fallback-Regeln „erfinden“, wenn kein Regelplan matcht →
  `REGELPLAN_NICHT_GEFUNDEN`
