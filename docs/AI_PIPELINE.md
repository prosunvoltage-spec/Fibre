# AI_PIPELINE — VRA-NVT-Automation

> Wie Bild-KI und OCR im System eingesetzt werden.
> Kernprinzip: **KI liefert Beobachtungen, keine Entscheidungen.**
> Alle Modelle sind austauschbare Adapter, alle Ausgaben strukturiertes JSON.

---

## 1. Aufgabenverteilung KI vs. Rule Engine

| Aufgabe                                       | Wer       |
| --------------------------------------------- | --------- |
| Bild verstehen (Gehweg? Fahrbahn? …)          | Vision-Provider |
| Text im Bild lesen (NVT-Nummer, Adresse)      | OCR-Provider |
| Straßenklasse aus Adresse                     | Geodata-Provider (OSM) |
| Regelplan auswählen                           | **Rule Engine** (deterministisch) |
| Menschenlesbare Begründung formulieren        | Vision-Provider (nur Text, keine Fachaussage) |
| Ähnliche Referenzfälle finden                 | Vision oder Embedding-Provider |

Das KI-System **wählt nie den Regelplan**. Es liefert nur den Input, den die
Rule Engine benötigt.

---

## 2. Provider-Abstraktion

```
app/vision/base.py
```

```python
class VisionProvider(Protocol):
    id: str
    version: str

    def analyze_photos(
        self,
        photos: list[PhotoBytes],
        prompt: LoadedPrompt,
        response_schema: type[BaseModel],
    ) -> ProviderResponse: ...

    def compare_references(
        self,
        subject: PhotoBytes,
        candidates: list[ReferencePhoto],
        top_k: int = 5,
    ) -> list[SimilarityHit]: ...


class OCRProvider(Protocol):
    id: str
    version: str
    def ocr_photo(self, photo: PhotoBytes) -> OcrResult: ...


class GeoProvider(Protocol):
    id: str
    def geocode(self, address: str) -> GeoResult | None: ...
    def road_classification(self, lat: float, lon: float) -> RoadClass | None: ...
```

**Default-Implementierungen:**
- `AnthropicVisionProvider` — Claude Sonnet/Opus mit Vision
- `TesseractOCRProvider` — offline OCR
- `NominatimGeoProvider` — OSM Nominatim (opt-in)

**Weitere Implementierungen** können später ergänzt werden ohne die Rule Engine
anzufassen. Auswahl per `.env`:

```
VISION_PROVIDER=anthropic
VISION_MODEL=claude-…
OCR_PROVIDER=tesseract
GEO_PROVIDER=nominatim
```

---

## 3. Prompt-Management

Alle Prompts liegen als **versionierte Markdown-Dateien** in `/prompts/`:

```
prompts/
├── environment_analysis.md      # Foto → EnvironmentModel-JSON
├── traffic_analysis.md          # Foto + WorkArea → TrafficUserAssessment[]
├── ruleplan_reasoning.md        # Menschenlesbare Begründung zum Rule-Engine-Vorschlag
├── visualization.md             # Symbol-Positions-Vorschlag (Overlay)
└── document_generation.md       # Textbausteine für Word (nur Formulierungshilfe)
```

**Regeln für Prompts:**
- Jede Datei beginnt mit YAML-Frontmatter: `version`, `expected_schema`, `notes`
- SHA256 der Datei landet als `prompt_hash` in jeder `Decision`/`EnvironmentAnalysis`
- Änderungen an Prompts sind versionierte Commits → Traceable Regressions
- Prompts **verbieten** das Wählen eines Regelplans ausdrücklich:
  > „Wähle keinen Regelplan. Beschreibe nur die Szene. Wenn du unsicher bist,
  > setze das Feld auf `unknown`.“

Beispiel-Frontmatter:

```markdown
---
version: 3
purpose: environment_analysis
expected_schema: EnvironmentAnalysisSchema
model_capabilities: [vision]
allow_free_text: false
---
```

---

## 4. Response-Schema (streng, Pydantic)

Vision-Antworten werden **immer** gegen ein Pydantic-Schema validiert.
Beispiel für Environment-Analyse:

```python
class VisionEnvironmentResponse(BaseModel):
    # Alle Felder aus EnvironmentAnalysis, aber ohne DB-IDs
    road_present: Ternary
    sidewalk_present: Ternary
    cycleway_present: Ternary
    ...
    nvt_position: Literal[...]
    sidewalk_width_m: Decimal | None    # None wenn unklar
    ...
    vision_confidence: Decimal          # muss zwischen 0 und 1 liegen
    uncertainties: list[str]            # freiwilliger Zusatz für Prüfbericht
    manual_review_suggested: bool
    contradictions: list[str] = []      # bei Multi-Foto-Input

    class Config:
        extra = "forbid"                # unbekannte Keys → Validation-Error
```

**Kein `str`-Feld für Regelplan-Empfehlung**. Selbst wenn das Modell ungefragt
einen Regelplan nennt, wird er verworfen (nicht persistiert, nicht angezeigt).

---

## 5. Retry & Fallback

```
attempt 1: strict schema
  ↳ ok?               → done
  ↳ pydantic error?   → attempt 2 (mit Fehlermeldung als Reminder)
  ↳ safety refusal?   → MANUELLE_PRUEFUNG
  ↳ timeout?          → attempt 2

attempt 2: strict schema
  ↳ ok?               → done
  ↳ error again?      → attempt 3 mit „bitte antworte NUR mit JSON …“ Vorspann
  ↳ timeout?          → MANUELLE_PRUEFUNG

attempt 3:
  ↳ ok?               → done, aber warning "vision_retries=3"
  ↳ error?            → MANUELLE_PRUEFUNG mit reason "vision_invalid_after_retries"
```

Fehler werden strukturiert geloggt (kein Foto in Logs), inkl. Prompt-Hash und
Fehlermeldung.

---

## 6. Multi-Foto-Aggregation

Ein NVT hat oft mehrere Perspektiven (Front, Straßenseite, gegenüberliegender
Gehweg, Rückseite …).

**Vorgehen:**
1. Alle Photos werden **in einem einzigen** Vision-Aufruf gesendet (Kontext-fördernd)
2. Prompt fordert das Modell explizit, für jede Frage eine Antwort zu geben,
   die aus **allen** Fotos abgeleitet ist
3. Wenn das Modell in `contradictions` etwas listet, oder wenn dasselbe Feld
   in zwei separaten Aufrufen (falls doch nötig) unterschiedlich beantwortet
   wird → `MANUELLE_PRUEFUNG`

Wenn ein Provider Multi-Image nicht unterstützt: pro Foto einen Aufruf, dann
aggregieren mit **konservativer** Aggregation (mind. eine `NO` überschreibt
`YES`? Nein — pro Feld eine explizite Aggregationsregel in
`app/classification/environment_builder.py`; Default: bei Widerspruch →
`UNKNOWN + contradiction`).

---

## 7. Halluzinations-Schutz

**Schutzmaßnahmen im Prompt:**
- „Wähle keinen Regelplan.“
- „Wenn eine Breite nicht sicher aus dem Bild ableitbar ist, antworte mit `null`
  im Feld und ergänze `uncertainties`.“
- „Zitiere keine Rechtsquellen. Wir verwenden nur unsere eigene Knowledge Base.“
- „Erfinde keine Adressen. Wenn im Bild kein Text sichtbar ist, antworte mit `null`.“

**Schutz im Code:**
- Pydantic `extra="forbid"` → verhindert Zusatzfelder wie `recommended_ruleplan`
- Post-Validator: alle `str`-Felder werden gegen ein Blocklist geprüft
  (`"§ 45 StVO"`, `"RSA 21 schreibt vor"`, …) — wenn diese vorkommen ohne
  entsprechendes Knowledge-Base-Match → Warning + Feld auf leer setzen
- Wenn das Modell eine Adresse liefert, wird sie mit OCR-Ergebnis gecrosscheckt;
  Divergenz → `contradiction`

**Quellenpflicht:**
Jede fachliche Aussage in `Decision.reasons`, die eine Regelwerks-Referenz
enthält, muss auf einen Eintrag in `/knowledge/` verweisen. Der Validator prüft,
dass `source_document` als Datei existiert. Wenn nicht → Aussage wird
weggeworfen und stattdessen: „Quelle nicht vorhanden.“

---

## 8. Rate-Limiting & Kosten

- **Concurrency** konfigurierbar (`VISION_MAX_CONCURRENCY`, Default 4)
- **Backoff** exponentiell bei 429/503
- **Kosten-Logging** pro Aufruf: `model_id`, `input_tokens`, `output_tokens`,
  `estimated_cost_eur` → aggregiert pro Projekt in `analysis_report.html`
- **Batching**: falls Provider Batch-API bietet, nutzen; sonst `asyncio.gather`
  mit Semaphore

---

## 9. Similarity-Search / Referenzfall-Vergleich

**Zweck:** Reviewer bekommt eine Liste ähnlicher Referenzfälle als
Orientierung (nicht als Entscheidung).

**Ansatz A (default, kostenfrei):** strukturiert-basiert.
- Für neuen NVT: `EnvironmentAnalysisSchema` als Feature-Vektor kodieren
  (One-Hot für Ternary-Felder + normalisierte numerische Werte)
- Cosine-Similarity gegen alle Referenzfälle
- Top-5 anzeigen

**Ansatz B (optional, später):** Vision-Embedding-basiert.
- Foto-Embedding via Provider (z.B. Claude-Vision oder separater Embedding-Provider)
- ANN-Suche (FAISS)

**Wichtig:** Similarity-Score ist **nur Anzeige**, geht nie in die Rule Engine
als Entscheidungsgrundlage ein.

---

## 10. Datenschutz

**Fotos sind personenbezogen** (Kennzeichen, Gesichter, Grundstücke).

- **Opt-in pro Projekt**: Cloud-KI nur wenn Projekt-Flag `use_cloud_vision=true`
- **Blur-Vorverarbeitung** optional (Gesichter/Kennzeichen unkenntlich machen
  vor Cloud-Upload) — Modul `app/preprocess/anonymize.py` (Phase 8+)
- **Prompt-Content-Log** enthält keine Foto-Bytes, nur Prompt-Hash + Response-Meta
- **Kein Training-Consent**: bei allen Providern muss die entsprechende
  Setting-Konfiguration dokumentiert sein (Anthropic, OpenAI etc.)

---

## 11. Interner Prüfbericht vs. finales Word

**Intern (`analysis_report.html`, `analyses.jsonl`):**
- LLM-Rohantwort
- Prompt-Hash
- Confidence-Werte
- Rule-Engine-Trace
- Kosten
- Retries
- Modellversion

**Final (`VRA_NVT_Gesamt.docx`):**
- **Kein** LLM-Rohtext
- **Kein** Confidence-Wert
- **Kein** Prompt-Ausschnitt
- **Nur** fachlich formulierte Zusammenfassung: „Verkehrssituation:
  einseitiger Gehweg an Wohnstraße; NVT im Seitenbereich. Fußverkehr wird
  über gegenüberliegenden Gehweg geführt. Regelplan: B1/2.“

Der Übergang von intern → extern läuft durch einen expliziten „Formulierungs-Prompt“
(`document_generation.md`), der aber nur die bereits **freigegebene** Entscheidung
in geglättete Sprache übersetzt — er darf keine neuen Fakten ergänzen.

---

## 12. Testbarkeit

- **Mock-Provider** `FakeVisionProvider` mit hinterlegten Antworten pro Testfoto
- **Contract-Tests**: jeder Provider muss ein Contract-Test-Suite bestehen
  (`tests/vision/test_contract.py`) — invaliden JSON zurückgeben lassen und
  prüfen dass Retry/Fallback greift
- **Regression**: 25 Referenzfotos mit gepinnter Mock-Response ergeben stabile
  Baseline-Analysen
- **Live-Test** (manuell, nicht in CI): kleines Skript
  `scripts/live_test_vision.py` prüft einen echten NVT gegen den konfigurierten
  Provider — braucht API-Key

---

## 13. Was die AI-Pipeline NICHT tut

- **Nicht** Regelpläne auswählen
- **Nicht** rechtliche Aussagen treffen
- **Nicht** Confidence in „safe/unsafe“ übersetzen
- **Nicht** Referenzfälle als Rechtsgrundlage behandeln
- **Nicht** Adressen erfinden (bei kein Text: `null`)
- **Nicht** RSA-21-Inhalte aus dem Modell-Wissen ergänzen
