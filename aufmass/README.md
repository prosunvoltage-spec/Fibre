# Digitales Aufmaßsystem – Albachten / Hiltrup West

Aufmaß im Browser erfassen → ein Klick → fertig ausgefülltes Original-PDF.
Zwei Blätter: **HK-Arbeiten** und **Hausanschlüsse (NE3)**.

Das Blanko-Blatt wird dabei **nicht nachgebaut**: die Originalseite bleibt
unverändert (Logo, Tabelle, Überschriften, Unterschriftsbereiche) und die
eingegebenen Werte werden exakt in die vorhandenen Zellen gesetzt.

## Benutzen

Eine einzige Datei: `index.html`. Nichts zu installieren, kein Server, keine
Anmeldung – läuft auf Handy, Tablet und PC.

**Öffnen:** Datei doppelklicken, oder unter `…/aufmass/` auf der Website
aufrufen und auf dem Handy zum Startbildschirm hinzufügen.

1. Oben das **Blatt wählen**: HK-Arbeiten oder Hausanschlüsse.
2. Kopfdaten ausfüllen. Ort, Unternehmen und das heutige Datum sind
   vorbelegt, beim HA-Blatt zusätzlich Projektstatus und die Prozentwerte.
3. Zeilen füllen – was in eine Zeile gehört, unterscheidet sich je Blatt
   (siehe unten). Position und Einheit erscheinen automatisch.
4. Optional **Unterschrift und Stempel** ankreuzen.
5. **PDF erstellen** – die Datei heißt
   `Aufmass_<HK|HA>_<NVT-Gebiet>_<Datum>.pdf`.

Unter den Zeilen stehen die **Summen je Position** – zur Kontrolle vor der
Unterschrift. Der Entwurf wird je Blatt laufend im Browser gespeichert und
ist nach dem Schließen noch da. Jedes Blatt fasst 30 Zeilen.

### Offline

Die PDF-Bibliothek (`pdf-lib`) wird von einem CDN geladen; nach dem ersten
Aufruf liegt sie im Browser-Cache. Für echten Offline-Betrieb einmalig
[`pdf-lib.min.js`](https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js)
herunterladen und neben `index.html` legen – die Seite bevorzugt die lokale
Datei automatisch. Beide Blanko-Vorlagen stecken bereits in der HTML-Datei.

## Die zwei Blätter

Oben in der Kopfleiste wird gewählt, welches Blatt gefüllt wird. Tätigkeiten,
Kopffelder und Zielvorlage wechseln mit. **Die Entwürfe bleiben getrennt** –
zwischen den Blättern hin- und herspringen verliert nichts.

Die beiden Blätter sind unterschiedlich gebaut:

| | HK-Arbeiten | Hausanschlüsse (NE3) |
|---|---|---|
| Eine Zeile ist … | eine Tätigkeit | ein Hausanschluss |
| Zeilenfelder | NVT | Straße, HA Nr., Anzahl WE |
| Mengen je Zeile | eine, Spalte per Auswahl | fünf, feste Spalten |
| Bemerkung | ja | nein (kein Platz im Blatt) |

Beim HK-Blatt bestimmt die gewählte Tätigkeit, in welche Mengenspalte der
Wert wandert. Das HA-Blatt hat je Zeile „Anzahl WE“ – es ist erkennbar für
**einen Hausanschluss pro Zeile** gedacht, mit mehreren Mengen nebeneinander.
Deshalb gibt es dort kein Tätigkeits-Auswahlfeld, sondern fünf Mengenfelder.

### Katalog HK-Arbeiten

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

### Katalog Hausanschlüsse

| Menge | Position | Einheit | Spalte im Blatt |
|---|---|---|---|
| Eingeblasene Kabellänge | 02.01.01.01 | m | 5 |
| Montage Gf-AP EFH + MFH | 02.01.01.02 | Stk | 6 |
| Installation Gf-TA EFH | 02.01.01.04 | Stk | 7 |
| Zusätzlicher Spleiß | 02.01.01.03 | Stk | 8 |
| Stunde Monteur Glasfaser | 02.07.01.03 | h | 9 |

Die Bezeichnungen sind hier die der **Spaltenüberschriften**, nicht die des
Leistungsverzeichnisses – so ist beim Eintragen sichtbar, in welche Spalte
ein Wert wandert. Im LV heißen sie „Hausanschluss Gf-Kabel in Mikrorohr…“,
„Montage Gf-AP“, „Zusätzliches Spleißen einer Faser“ und „Installation
Gf-TA EFH“. Beim HK-Blatt ist es umgekehrt: dort wird der Name in die
Spalte „Tätigkeit“ gedruckt, deshalb stehen dort die LV-Bezeichnungen.

## Zwei Fehler in den gelieferten Blanko-Blättern

Beide Vorlagen tragen Positionsnummern, die nicht aufgehen. Das Werkzeug
ordnet die Mengen deshalb grundsätzlich nach der **Spaltenüberschrift** zu,
nie nach der aufgedruckten Nummer. Die aufgedruckten Nummern werden nicht
überschrieben – das Layout bleibt unangetastet.

**HK-Blatt, 02.05.01:** Spalte 4 heißt „GF-Kabel vorb. & Spleißen (bis
96F.)“. Diese Position gibt es im Leistungsverzeichnis nicht; es existiert
nur **eine** Position fürs Vorbereiten und Spleißen. Dadurch sind die
Nummern der folgenden Spalten um eins zu hoch:

| Spalte | aufgedruckt | laut LV |
|---|---|---|
| 3 – GF-Kabel vorb. & Spleißen (bis 24F.) | 02.05.01.01 | 02.05.01.01 ✓ |
| 4 – GF-Kabel vorb. & Spleißen (bis 96F.) | 02.05.01.02 | entfällt, bleibt leer |
| 5 – Montage und Spleißen von Kopplern | 02.05.01.03 | 02.05.01.02 |
| 6 – Zusätzliches Spleißen weiterer Fasern | 02.05.01.04 | 02.05.01.03 |

**HA-Blatt, zwei falsche Nummern:** „Montage Gf-AP“ trägt aufgedruckt
02.01.01.01 – das ist die Nummer der Kabellänge, dieselbe Nummer stand also
auf zwei Spalten. Und „Zusätzlicher Spleiß“ trägt 04.02.01.01.03, gehört
laut LV aber in denselben Block:

| Spalte | aufgedruckt | laut LV |
|---|---|---|
| 5 – Eingeblasene Kabellänge (m) | 02.01.01.01 | 02.01.01.01 ✓ |
| 6 – Montage Gf-AP EFH + MFH (Stk) | 02.01.01.01 | 02.01.01.02 |
| 7 – Installation Gf-TA EFH (Stk) | 02.01.01.04 | 02.01.01.04 ✓ |
| 8 – Zusätzlicher Spleiß (Stk) | 04.02.01.01.03 | 02.01.01.03 |
| 9 – Stunde Monteur Glasfaser | 02.07.01.03 | unbestätigt |

Sauber wird beides erst mit aktualisierten Blanko-Blättern vom Auftraggeber.

## Unterschrift und Stempel

Beim Export kann Unterschrift samt Stempel unter der Linie bei
„Auftragnehmer“ eingesetzt werden. Das Bild wird einmal hinterlegt und
liegt **nur im Browser des jeweiligen Geräts** – nicht im Repo. Jeder
unterschreibt also mit seiner eigenen.

Am besten ein PNG mit freigestelltem Hintergrund. Weiß im Bild wird beim
Hinterlegen automatisch entfernt, ein Foto auf weißem Papier reicht also.
Nach dem Leeren der Browserdaten muss das Bild neu hinterlegt werden.

## Katalog erweitern

In `index.html` die Liste `BLAETTER` bearbeiten: `mengen` ergänzen, dabei
`spalte` auf die gemessenen Kanten der Zielspalte setzen. Ein ganz neues
Blatt braucht zusätzlich seine normalisierte Vorlage als base64 (siehe
„Zur Technik“).

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Das Werkzeug – beide Blätter, Eingabe und PDF-Erstellung |
| `vorlage/Blanko_Aufmassblatt.pdf` | HK-Blatt, wie geliefert |
| `vorlage/Blanko_quer.pdf` | HK-Blatt entdreht (steckt in `index.html`) |
| `vorlage/Blanko_HA.pdf` | HA-Blatt, wie geliefert |
| `vorlage/Blanko_HA_quer.pdf` | HA-Blatt entdreht (steckt in `index.html`) |

## Zur Technik

Die Werte werden nicht in Formularfelder geschrieben – das Blatt hat keine.
Sie werden als Text auf die Originalseite gesetzt, an aus den Gitterlinien
gemessenen Koordinaten. Nur die drei vorgedruckten Angaben Ort/Datum,
Unternehmen und BV werden vorher weiß überdeckt; die Linien darunter bleiben
stehen.

Beide gelieferten Vorlagen sind um 90° gedrehte Seiten. Für das Werkzeug
wurden sie einmalig auf echtes Querformat normalisiert
(`vorlage/*_quer.pdf`): Seitendrehung entfernt, MediaBox getauscht und
die Transformation `0 -1 1 0 0 595.22 cm` an den Anfang des Inhaltsstroms
gestellt. Der Inhalt ist unverändert – „Albachten“ liegt vorher wie nachher
auf (184,0 | 83,7). Dadurch entsprechen die gemessenen Zellkoordinaten
direkt den PDF-Koordinaten, und im Browser genügt
`y_pdf = 595,22 − y_gemessen` ohne Rotationsmatrix.
