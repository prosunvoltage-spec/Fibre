# Regelplan-Bibliothek

Ein Regelplan pro Unterordner. Der Ordnername ist die maschinenlesbare ID
(z.B. `B1_2`, `B2_2`, `B1_15`, `VZP1`). Die fachliche ID im Metadaten-JSON
darf Sonderzeichen enthalten (`B1/2`).

## Erwartete Dateien pro Ordner

```
B1_2/
├── metadata.json     # PFLICHT — wird von RulePlanLoader validiert
├── plan.pdf          # Regelplan-Zeichnung (nicht ins Git)
└── preview.png       # Vorschau für die UI (nicht ins Git)
```

## `metadata.json` — Struktur

```jsonc
{
  "id": "B1/2",
  "name": "Regelplan B I/2 modifiziert",
  "quelle": "RSA 21 Teil D",
  "version": "08.21",
  "beschreibung": "Straße mit geringer Verkehrsstärke oder in geschwindigkeitsreduziertem Bereich",
  "verkehrsraum": [],
  "geeignet_fuer": [],
  "voraussetzungen": [
    {
      "condition": "Restfahrbahnbreite ≥ 3,00 m",
      "machine_predicate": "remaining_roadway_ge",
      "args": { "min_m": 3.0 },
      "source_document": "Auflagen Stadt Münster",
      "source_reference": "Standardauflage §3",
      "source_page": null,
      "notes": null
    }
  ],
  "ausschlusskriterien": [],
  "fussverkehr": {},
  "radverkehr": {},
  "fahrverkehr": {},
  "besondere_hinweise": [],
  "allowed_symbols": []
}
```

## Vollständigkeits-Regel

Der Loader setzt automatisch `is_complete = false`, wenn eines dieser Felder
leer ist:

- `verkehrsraum`
- `geeignet_fuer`
- `voraussetzungen`
- `allowed_symbols`

Zusätzlich braucht **jede** Voraussetzung / jedes Ausschlusskriterium eine
`source_document`-Angabe.

**Solange `is_complete = false` ist, führt der Regelplan niemals zu
`AUTO_VORSCHLAG` oder `AUTO_FREIGABE_VORBEREITET`** — er kann als Kandidat
angezeigt werden, aber die Freigabe ist blockiert.

## Neuen Regelplan hinzufügen

1. Ordner `XYZ/` anlegen
2. `metadata.json` gemäß Struktur oben erstellen
3. `plan.pdf` und optional `preview.png` beilegen
4. Server startet neu → Loader findet den Regelplan automatisch

Kein Code-Change nötig.

## Initialer Bestand

Die Metadaten für **VZP1, B1_2, B2_2, B1_15** wurden aus der Roxel-VRA
(S. 53–56) angelegt, mit `is_complete = false`. Die inhaltlichen Felder
(`voraussetzungen`, `ausschlusskriterien` …) müssen vom Fachanwender aus der
Original-RSA-21-Vorlage befüllt werden.
