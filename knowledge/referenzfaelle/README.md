# Referenzfälle

Ein Ordner pro NVT-Nummer (z.B. `NVT_7107/`). Jeder Ordner enthält eine
`nvt.json` mit den Metadaten des Falls und optional ein `photo.png`.

## Zweck

- **Regressionstests**: prüfen, dass Änderungen am System nicht zu
  Widersprüchen mit historischen Freigaben führen
- **Similarity-Search**: für neue NVT-Fälle ähnliche Referenzen anzeigen
- **Trainings-/Dokumentationsdatenbank**: Fachanwender können bestehende
  Zuordnungen nachschlagen

## Wichtig

Ein Referenzfall ist **keine Rechtsgrundlage**. Er dokumentiert nur, wie
ein bestimmter NVT in einer bestehenden freigegebenen VRA behandelt wurde.
Das Feld `kind` ist immer auf `"reference"` fixiert und wird von der Rule
Engine ignoriert — die Rule Engine entscheidet ausschließlich anhand der
Regelplan-Bibliothek.

## `nvt.json` — Struktur

```jsonc
{
  "nvt_number": "7107",
  "source_file": "Roxel_alle_NVT_Einblasarbeiten_...02072026.pdf",
  "source_page": 11,
  "address": {
    "street": "Roxeler Straße",
    "house_number": "579",
    "postal_code": "48161",
    "city": "Münster"
  },
  "ruleplan_label": "B2/2",       // wie in der VRA eingezeichnet
  "special_case": null,           // z.B. "Privatfläche", "Betriebsgelände"
  "notes": "Hauptverkehrsstraße, NVT am Fahrbahnrand",
  "lageplan_pages": [12, 13],     // Seitenzahlen des Lageplans in der PDF
  "extracted_at": null,           // gefüllt vom Extraction-Skript
  "kind": "reference"
}
```

## Binaries

`photo.png` wird per `scripts/extract_reference_cases.py` aus der
Referenz-PDF erzeugt und ist in `.gitignore` — also nur lokal vorhanden.
Das Skript aktualisiert `extracted_at` in der `nvt.json`, verändert aber
sonst keine Metadatenfelder.

## Neuen Referenzfall hinzufügen

1. Ordner `NVT_XYZ/` anlegen
2. `nvt.json` gemäß Struktur oben erstellen (Adresse, Regelplan-Label, Seite)
3. Optional: Foto per `scripts/extract_reference_cases.py --nvt XYZ` extrahieren
