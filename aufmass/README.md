# Digitales Aufmaßsystem – HK Albachten / HK Hiltrup West

Eingabe in Excel → ein Klick → fertig ausgefülltes Aufmaß im Original-PDF.

Das Blanko-Blatt wird dabei **nicht nachgebaut**: die Originalseite bleibt
unverändert (Logo, Tabelle, Überschriften, Unterschriftsbereiche) und die
eingegebenen Werte werden exakt in die vorhandenen Zellen gesetzt.

## Dateien

| Datei | Zweck |
|---|---|
| `Aufmassblatt.xlsx` | Eingabemaske mit Dropdowns – hier wird gearbeitet |
| `PDF erstellen.bat` | Windows: doppelklicken → PDF entsteht im selben Ordner |
| `vorlage/Blanko_Aufmassblatt.pdf` | Das Original-Aufmaßblatt (nicht ändern) |
| `aufmass_pdf.py` | Liest die Excel-Datei und startet die PDF-Erstellung |
| `pdf_fill.py` | Trägt die Werte in das Original-PDF ein |
| `layout.py` | Tätigkeitskatalog und vermessene Zellkoordinaten |
| `make_template.py` | Erzeugt `Aufmassblatt.xlsx` neu (nach Katalogänderungen) |
| `vba/PDFErstellen.bas` | Optional: Button „PDF erstellen“ direkt in Excel |

## Bedienung

1. `Aufmassblatt.xlsx` öffnen.
2. Kopfbereich ausfüllen: Ort, Datum, NVT Gebiet, Unternehmen, BV, Projekt,
   Betriebsnetz. Ort, Unternehmen und BV sind vorbelegt.
3. Pro Zeile eintragen:
   - **NVT** – frei
   - **Tätigkeit** – Auswahl aus dem Dropdown
   - **Menge** – Zahl
   - **Bemerkung** – optional, erscheint im PDF hinter der Tätigkeit
   
   **Position** und **Einheit** füllen sich automatisch (grau hinterlegt,
   nicht ausfüllen).
4. `PDF erstellen.bat` doppelklicken. Das Ergebnis heißt
   `Aufmass_<NVT-Gebiet>_<Datum>.pdf` und liegt im selben Ordner.

Das Blatt hat 30 Zeilen. Werden mehr Positionen gebraucht, auf mehrere
Blätter aufteilen.

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

## Einrichtung (einmalig, pro Rechner)

Benötigt wird Python 3 – bei der Installation **„Add Python to PATH"**
ankreuzen. Die erforderlichen Bibliotheken (`openpyxl`, `pymupdf`) installiert
`PDF erstellen.bat` beim ersten Lauf selbst.

Ohne Batch-Datei geht es auch direkt:

```bash
pip install openpyxl pymupdf
python aufmass_pdf.py Aufmassblatt.xlsx            # Ziel wird automatisch benannt
python aufmass_pdf.py Aufmassblatt.xlsx Ziel.pdf   # oder Ziel selbst festlegen
```

### Optional: Button in Excel

`vba/PDFErstellen.bas` enthält ein Makro. Einbau ist im Kopf der Datei
beschrieben: Mappe als `.xlsm` speichern, Modul importieren, eine Form
einfügen und ihr das Makro `PDFErstellen` zuweisen. Damit liegt der
„PDF erstellen“-Button direkt im Tabellenblatt.

## Katalog erweitern

Neue Tätigkeiten in `layout.py` unter `TAETIGKEITEN` ergänzen – dabei `col`
auf die passende Mengenspalte des PDFs setzen (0–8) – und danach die
Eingabemaske neu erzeugen:

```bash
python make_template.py Aufmassblatt.xlsx
```

Kommen im PDF **neue Spalten** hinzu, müssen zusätzlich die Koordinaten in
`layout.py` (`COLS`) angepasst werden.
