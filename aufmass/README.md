# Digitales Aufmaßsystem – HK Albachten / HK Hiltrup West

Aufmaß im Browser erfassen → ein Klick → fertig ausgefülltes Original-PDF.

Das Blanko-Blatt wird dabei **nicht nachgebaut**: die Originalseite bleibt
unverändert (Logo, Tabelle, Überschriften, Unterschriftsbereiche) und die
eingegebenen Werte werden exakt in die vorhandenen Zellen gesetzt.

## Benutzen

Eine einzige Datei: `index.html`. Nichts zu installieren, kein Server, keine
Anmeldung – läuft auf Handy, Tablet und PC.

**Öffnen:** Datei doppelklicken, oder unter `…/aufmass/` auf der Website
aufrufen und auf dem Handy zum Startbildschirm hinzufügen.

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

Die Positionsnummern folgen dem **Leistungsverzeichnis**.

| Tätigkeit | Position | Einheit | Spalte im Blatt |
|---|---|---|---|
| Einblasen HK 24F | 02.02.01.02 | m | 1 |
| Einblasen HK 96F | 02.02.01.01 | m | 2 |
| Glasfaserkabel vorbereiten und spleißen | 02.05.01.01 | St | 3 |
| Montage und Spleißen von Kopplern | 02.05.01.02 | St | 5 |
| Zusätzliches Spleißen weiterer Fasern | 02.05.01.03 | St | 6 |
| GF ungespleißt ablegen | 02.03.01.03 | m | 7 |
| Montieren EZA 12mm | 02.04.01.02 | St | 8 |
| Stunden Monteur | 02.07.01.03 | h | 9 |

Die Tätigkeit steuert, **in welche Mengenspalte** des PDFs der Wert wandert.

### Das Blanko-Blatt ist bei 02.05.01 veraltet

Spalte 4 des gelieferten Blattes heißt „GF-Kabel vorb. & Spleißen (bis
96F.)“. Diese Position gibt es im Leistungsverzeichnis nicht; es existiert
nur **eine** Position fürs Vorbereiten und Spleißen. Dadurch sind die
aufgedruckten Nummern der drei folgenden Spalten um eins zu hoch:

| Spalte | aufgedruckt | laut LV |
|---|---|---|
| 3 – GF-Kabel vorb. & Spleißen (bis 24F.) | 02.05.01.01 | 02.05.01.01 ✓ |
| 4 – GF-Kabel vorb. & Spleißen (bis 96F.) | 02.05.01.02 | entfällt |
| 5 – Montage und Spleißen von Kopplern | 02.05.01.03 | 02.05.01.02 |
| 6 – Zusätzliches Spleißen weiterer Fasern | 02.05.01.04 | 02.05.01.03 |

Das Werkzeug ordnet die Mengen deshalb nach der **Spaltenüberschrift** zu,
nicht nach der aufgedruckten Nummer. Spalte 4 bleibt dauerhaft leer. Die
aufgedruckten Nummern werden nicht überschrieben – das Layout bleibt
unangetastet. Sauber wird das erst, wenn der Auftraggeber ein aktualisiertes
Blanko-Blatt liefert.

Katalog erweitern: in `index.html` die Liste `TAETIGKEITEN` ergänzen und
`spalte` auf die passende Mengenspalte setzen (0–8, also Spalte im Blatt
minus 1). Kommen im PDF **neue Spalten** hinzu, müssen zusätzlich die
Koordinaten in `SPALTEN` angepasst werden.

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Das Werkzeug – Eingabe und PDF-Erstellung in einem |
| `vorlage/Blanko_Aufmassblatt.pdf` | Das Original, wie geliefert |
| `vorlage/Blanko_quer.pdf` | Dasselbe Blatt ohne Seitendrehung (steckt in `index.html`) |

## Zur Technik

Die Werte werden nicht in Formularfelder geschrieben – das Blatt hat keine.
Sie werden als Text auf die Originalseite gesetzt, an aus den Gitterlinien
gemessenen Koordinaten. Nur die drei vorgedruckten Angaben Ort/Datum,
Unternehmen und BV werden vorher weiß überdeckt; die Linien darunter bleiben
stehen.

Die gelieferte Vorlage ist eine um 90° gedrehte Seite. Für das Werkzeug
wurde sie einmalig auf echtes Querformat normalisiert
(`vorlage/Blanko_quer.pdf`): Seitendrehung entfernt, MediaBox getauscht und
die Transformation `0 -1 1 0 0 595.22 cm` an den Anfang des Inhaltsstroms
gestellt. Der Inhalt ist unverändert – „Albachten“ liegt vorher wie nachher
auf (184,0 | 83,7). Dadurch entsprechen die gemessenen Zellkoordinaten
direkt den PDF-Koordinaten, und im Browser genügt
`y_pdf = 595,22 − y_gemessen` ohne Rotationsmatrix.
