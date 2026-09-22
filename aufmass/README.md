# Digitales Aufmaßsystem – HK Albachten / HK Hiltrup West

Aufmaß im Browser erfassen → ein Klick → fertig ausgefülltes Original-PDF.

Das Blanko-Blatt wird dabei **nicht nachgebaut**: die Originalseite bleibt
unverändert (Logo, Tabelle, Überschriften, Unterschriftsbereiche) und die
eingegebenen Werte werden exakt in die vorhandenen Zellen gesetzt.

## Das Werkzeug: `index.html`

Eine einzige Datei. Nichts zu installieren, kein Server, keine Anmeldung –
läuft auf Handy, Tablet und PC.

**Öffnen:** Datei doppelklicken, oder unter `…/aufmass/` auf der Website
aufrufen und auf dem Handy zum Startbildschirm hinzufügen.

**Bedienen:**

1. Kopfdaten ausfüllen. Ort, Unternehmen, BV und das heutige Datum sind
   vorbelegt.
2. Pro Zeile: **NVT**, **Tätigkeit** (Auswahlliste), **Menge**, optional
   **Bemerkung**. Position und Einheit erscheinen automatisch.
3. **PDF erstellen** – die Datei heißt `Aufmass_<NVT-Gebiet>_<Datum>.pdf`.

Unter den Positionen stehen die **Summen je Tätigkeit** – zur Kontrolle vor
der Unterschrift. Der Entwurf wird laufend im Browser gespeichert und ist
nach dem Schließen noch da. Das Blatt fasst 30 Zeilen.

### Offline

Die PDF-Bibliothek (`pdf-lib`) wird von einem CDN geladen; nach dem ersten
Aufruf liegt sie im Browser-Cache. Für echten Offline-Betrieb einmalig
[`pdf-lib.min.js`](https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js)
herunterladen und neben `index.html` legen – die Seite bevorzugt die lokale
Datei automatisch. Die Blanko-Vorlage steckt bereits in der HTML-Datei.

## Tätigkeitskatalog

| Tätigkeit | Position | Einheit | Spalte im PDF |
|---|---|---|---|
| Einblasen HK 24F | 02.02.01.02 | m | 1 |
| Einblasen HK 96F | 02.02.01.01 | m | 2 |
| GF-Kabel vorb. & Spleißen (bis 24F.) | 02.05.01.01 | St | 3 |
| GF-Kabel vorb. & Spleißen (bis 96F.) | 02.05.01.02 | St | 4 |
| Montage und Spleißen von Kopplern | 02.05.01.03 | St | 5 |
| Zusätzliches Spleißen weiterer Fasern | 02.05.01.04 | St | 6 |
| GF ungespleißt ablegen | 02.03.01.03 | m | 7 |
| Montieren EZA 12mm | 02.04.01.02 | St | 8 |
| Stunden Monteur | 02.07.01.03 | h | 9 |

Die Tätigkeit steuert, **in welche Mengenspalte** des PDFs der Wert wandert.

Katalog erweitern: in `index.html` die Liste `TAETIGKEITEN` ergänzen und
`spalte` auf die passende Mengenspalte setzen (0–8). Kommen im PDF **neue
Spalten** hinzu, müssen zusätzlich die Koordinaten in `SPALTEN` angepasst
werden – und in `layout.py`, falls der Excel-Weg weiter genutzt wird.

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Das Werkzeug – Eingabe und PDF-Erstellung in einem |
| `vorlage/Blanko_Aufmassblatt.pdf` | Das Original, wie geliefert |
| `vorlage/Blanko_quer.pdf` | Dasselbe Blatt ohne Seitendrehung (steckt in `index.html`) |

### Alternativer Weg über Excel

Vor dem Browser-Werkzeug entstanden; funktioniert weiterhin, braucht aber
Python auf dem Rechner.

| Datei | Zweck |
|---|---|
| `Aufmassblatt.xlsx` | Eingabemaske mit Dropdowns |
| `PDF erstellen.bat` | Windows: doppelklicken → PDF im selben Ordner |
| `aufmass_pdf.py` | Liest die Excel-Datei, startet die PDF-Erstellung |
| `pdf_fill.py` | Trägt die Werte in das Original-PDF ein |
| `layout.py` | Tätigkeitskatalog und vermessene Zellkoordinaten |
| `make_template.py` | Erzeugt `Aufmassblatt.xlsx` neu |
| `vba/PDFErstellen.bas` | Optional: Button „PDF erstellen“ in Excel |

```bash
pip install openpyxl pymupdf
python aufmass_pdf.py Aufmassblatt.xlsx
```

## Zur Technik

Die Vorlage ist eine um 90° gedrehte Seite. Für das Browser-Werkzeug wurde
sie einmalig auf echtes Querformat normalisiert (`vorlage/Blanko_quer.pdf`):
Seitendrehung entfernt, MediaBox getauscht und die Transformation
`0 -1 1 0 0 595.22 cm` in den Inhaltsstrom gestellt. Der Inhalt ist
unverändert – „Albachten“ liegt vorher wie nachher auf (184,0 | 83,7).
Dadurch entsprechen die gemessenen Zellkoordinaten direkt den
PDF-Koordinaten, und im Browser genügt `y_pdf = 595,22 − y_gemessen`.
