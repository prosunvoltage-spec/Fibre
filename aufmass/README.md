# Digitales Aufmaßsystem – Albachten / Hiltrup West

Aufmaß im Browser erfassen → ein Klick → fertig ausgefülltes Original-PDF.
Drei Blätter: **HK-Arbeiten**, **Hausanschlüsse (NE3)** und **HA Tiefbau**.

Das Blanko-Blatt wird dabei **nicht nachgebaut**: die Originalseite wird
übernommen und die Werte werden in die vorhandenen Zellen gesetzt. Logo,
Kopfbereich und Unterschriftsfelder bleiben unangetastet.

Wo die gelieferten Blätter nicht zum Leistungsverzeichnis passen, wird beim
Export nachgebessert: eine Spalte entfällt, eine kommt dazu, vier falsche
Positionsnummern werden überschrieben. Siehe unten.

## Benutzen

Eine einzige Datei: `index.html`. Nichts zu installieren, kein Server, keine
Anmeldung – läuft auf Handy, Tablet und PC.

**Öffnen:** Datei doppelklicken, oder unter `…/aufmass/` auf der Website
aufrufen und auf dem Handy zum Startbildschirm hinzufügen.

1. Oben das **Blatt wählen**: HK-Arbeiten, Hausanschlüsse oder HA Tiefbau.
2. Kopfdaten ausfüllen. Ort, Unternehmen und das heutige Datum sind
   vorbelegt, beim HA-Blatt zusätzlich Projektstatus und die Prozentwerte.
3. Zeilen füllen – was in eine Zeile gehört, unterscheidet sich je Blatt
   (siehe unten). Position und Einheit erscheinen automatisch.
4. Optional **Unterschrift und Stempel** ankreuzen.
5. **PDF erstellen** – die Datei heißt
   `Aufmass_<Blatt>_<Kennung>_<Datum>.pdf`.

Die **Kennung** macht das PDF im Ordner wiedererkennbar. Sie kommt je nach
Blatt aus unterschiedlichen Feldern:

| Blatt | Kennung | Beispiel |
|---|---|---|
| HK-Arbeiten | NVT Gebiet | `Aufmass_HK_NVT_12_2026-09-22.pdf` |
| Hausanschlüsse | erste Adresse (Straße + HA Nr.) | `Aufmass_HA_Roxeler_Strasse-HA-101_2026-09-22.pdf` |
| HA Tiefbau | erste Adresse (Straße + Nr.) | `Aufmass_TB_Kleine_Breikamp-152_2026-09-22.pdf` |

Ist keine Adresse eingetragen, greift ersatzweise das NVT Gebiet; fehlt auch
das, steht `ohne-Angabe` im Namen. Umlaute werden umgeschrieben
(`Straße` → `Strasse`), damit der Name auf jedem System gleich aussieht.

Das **Datum steht als `2026-09-22`** am Ende. Dadurch sortieren sich die
Blätter eines NVT-Gebiets bzw. einer Adresse im Ordner von selbst nach
Datum.

Unter den Zeilen stehen die **Summen je Position** – zur Kontrolle vor der
Unterschrift. Der Entwurf wird je Blatt laufend im Browser gespeichert und
ist nach dem Schließen noch da. Die Blätter fassen 30 bzw. 31 Zeilen.

### Offline

Die PDF-Bibliothek (`pdf-lib`) wird von einem CDN geladen; nach dem ersten
Aufruf liegt sie im Browser-Cache. Für echten Offline-Betrieb einmalig
[`pdf-lib.min.js`](https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js)
herunterladen und neben `index.html` legen – die Seite bevorzugt die lokale
Datei automatisch. Alle drei Blanko-Vorlagen stecken bereits in der HTML-Datei.

## Die drei Blätter

Oben in der Kopfleiste wird gewählt, welches Blatt gefüllt wird. Tätigkeiten,
Kopffelder und Zielvorlage wechseln mit. **Die Entwürfe bleiben getrennt** –
zwischen den Blättern hin- und herspringen verliert nichts.

Die Blätter sind unterschiedlich gebaut:

| | HK-Arbeiten | Hausanschlüsse (NE3) | HA Tiefbau |
|---|---|---|---|
| Format | A4 quer | A4 quer | A4 hoch |
| Zeilen | 30 | 30 | 31 |
| Eine Zeile ist … | eine Tätigkeit | ein Hausanschluss | eine Adresse |
| Zeilenfelder | NVT | Straße, HA Nr., Anzahl WE | Straße, Nr., Fotodoku, Konnektiert, Zusatzaufwand |
| Mengen je Zeile | eine, Spalte per Auswahl | sechs, feste Spalten | keine |
| Bemerkung | ja | nein (kein Platz im Blatt) | nein |

Beim HK-Blatt bestimmt die gewählte Tätigkeit, in welche Mengenspalte der
Wert wandert. Das HA-Blatt hat je Zeile „Anzahl WE“ – es ist erkennbar für
**einen Hausanschluss pro Zeile** gedacht, mit mehreren Mengen nebeneinander.
Deshalb gibt es dort kein Tätigkeits-Auswahlfeld, sondern sechs Mengenfelder.

### HA Tiefbau

Dieses Blatt erfasst keine Mengen, sondern Adressen. Je Zeile:

| Spalte | Eingabe |
|---|---|
| Straße | frei |
| Nr. | frei |
| Fotodoku | Auswahl `Share` / `Dimamap` |
| Konnektiert | Auswahl `JA` / `NEIN` |
| Zusatzaufwand | Freitext |

Die **Skizzenfläche bleibt frei** – sie ist zum Zeichnen von Hand gedacht.

Die Vorlage kam als **ausgefülltes** Blatt einer anderen Baustelle. Die
Werte wurden einmalig entfernt – nicht nur weiß überdeckt, sondern aus dem
PDF gelöscht, damit keine fremden Daten mitlaufen.

**Die Tabelle wird beim Export neu gezogen.** Das gelieferte Blatt setzt die
Zeilen in zwei Blöcken nebeneinander (1–15 links, 16–31 rechts) und hat dort
keinen Platz für „Konnektiert“ und „Zusatzaufwand“ – die beiden bräuchten je
Block rund 125 pt, die es nicht gibt. Das Werkzeug zieht die Tabelle deshalb
als **einen Block mit 31 Zeilen und fünf Spalten** über die volle Breite.
Dafür entfällt das Band „Sonstige“ – der Zusatzaufwand steht jetzt je Zeile –
und die Skizzenfläche beginnt tiefer; sie bleibt rund 210 pt hoch.

Die Strichstärken stammen aus der Vorlage (Rahmen 1,332 pt, Zeilentrenner
0,72 pt, Kopfschrift 6,9 pt), damit die neue Tabelle nicht von den
gedruckten Linien abweicht.

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
| Normalstunde Monteur Glasfaser | 02.07.01.03 | h | 9 |

### Katalog Hausanschlüsse

| Menge | Position | Einheit | Spalte im Blatt |
|---|---|---|---|
| Eingeblasene Kabellänge | 02.01.01.01 | m | 5 |
| Montage Gf-AP EFH + MFH | 02.01.01.02 | Stk | 6 |
| Installation Gf-TA EFH | 02.01.01.04 | Stk | 7 |
| Zusätzlicher Spleiß | 02.01.01.03 | Stk | 8 |
| Montieren EZA-t 7 / 2,0-4,0 | 02.04.01.01 | Stk | 9 (neu) |
| Normalstunde Monteur Glasfaser | 02.07.01.03 | h | 10 (neu gezeichnet) |

Die Bezeichnungen sind hier die der **Spaltenüberschriften**, nicht die des
Leistungsverzeichnisses – so ist beim Eintragen sichtbar, in welche Spalte
ein Wert wandert. Im LV heißen die ersten vier „Hausanschluss Gf-Kabel in
Mikrorohr…“, „Montage Gf-AP“, „Zusätzliches Spleißen einer Faser“ und
„Installation Gf-TA EFH“.

Ausnahme sind die beiden Spalten, deren Kopf das Werkzeug ohnehin selbst
setzt – dort steht der LV-Wortlaut. Beim HK-Blatt ist es durchgehend so:
der Name wird in die Spalte „Tätigkeit“ gedruckt, deshalb stehen dort die
LV-Bezeichnungen.

## Falsche Positionsnummern in den Vorlagen

Beide Vorlagen tragen Nummern, die nicht aufgehen. Das Werkzeug ordnet die
Mengen nach der **Spaltenüberschrift** zu, nie nach der aufgedruckten
Nummer, und **überschreibt die vier falschen Nummern beim Export** – jeweils
an derselben Stelle, in derselben Größe und Strichstärke wie gedruckt.

**HK-Blatt, 02.05.01:** Spalte 4 heißt „GF-Kabel vorb. & Spleißen (bis
96F.)“. Diese Position gibt es im Leistungsverzeichnis nicht; es existiert
nur **eine** Position fürs Vorbereiten und Spleißen. Dadurch sind die
Nummern der folgenden Spalten um eins zu hoch:

| Spalte | aufgedruckt | laut LV |
|---|---|---|
| 3 – GF-Kabel vorb. & Spleißen (bis 24F.) | 02.05.01.01 | 02.05.01.01 ✓ |
| 4 – GF-Kabel vorb. & Spleißen (bis 96F.) | 02.05.01.02 | entfällt, Spalte wird entfernt |
| 5 – Montage und Spleißen von Kopplern | 02.05.01.03 | **02.05.01.02**, wird überschrieben |
| 6 – Zusätzliches Spleißen weiterer Fasern | 02.05.01.04 | **02.05.01.03**, wird überschrieben |

**HA-Blatt, zwei falsche Nummern:** „Montage Gf-AP“ trägt aufgedruckt
02.01.01.01 – das ist die Nummer der Kabellänge, dieselbe Nummer stand also
auf zwei Spalten. Und „Zusätzlicher Spleiß“ trägt 04.02.01.01.03, gehört
laut LV aber in denselben Block:

| Spalte | aufgedruckt | laut LV |
|---|---|---|
| 5 – Eingeblasene Kabellänge (m) | 02.01.01.01 | 02.01.01.01 ✓ |
| 6 – Montage Gf-AP EFH + MFH (Stk) | 02.01.01.01 | **02.01.01.02**, wird überschrieben |
| 7 – Installation Gf-TA EFH (Stk) | 02.01.01.04 | 02.01.01.04 ✓ |
| 8 – Zusätzlicher Spleiß (Stk) | 04.02.01.01.03 | **02.01.01.03**, wird überschrieben |
| 9 – Stunde Monteur Glasfaser | 02.07.01.03 | 02.07.01.03 ✓ |

Das exportierte Aufmaß stimmt damit mit dem LV überein. Die **Vorlagen
selbst** bleiben falsch – sauber wird das erst mit aktualisierten
Blanko-Blättern vom Auftraggeber.

## Eingriffe am Spaltenraster

Zwei Spalten passen nicht zum Leistungsverzeichnis und werden beim Export
verändert. Alles andere – Logo, Kopfbereich, Zeilenraster,
Unterschriftsfelder – bleibt unberührt.

**HK-Blatt: eine Spalte weniger.** „GF-Kabel vorb. & Spleißen (bis 96F.)“
gibt es nicht. Die Spalte wird entfernt und geht in die linke Nachbarspalte
auf: Kopf und Trennlinie werden weiß überdeckt, die Zeilentrenner an der
Nahtstelle in Originalstärke neu gezogen, der Kopf der zusammengefassten
Spalte mittig neu gesetzt. Er lautet jetzt „Glasfaserkabel vorbereiten und
spleißen / 02.05.01.01“ – der Zusatz „(bis 24F.)“ wäre falsch, weil die
verbliebene Position alle Faserzahlen abdeckt.

**HA-Blatt: eine Spalte mehr.** „Montieren EZA-t 7 / 2,0-4,0 (Stk),
02.04.01.01“ fehlt im Blatt. Sie nimmt den Platz der Monteurstunden ein;
die Stunden wandern in eine rechts neu gezeichnete Spalte gleicher Breite.
Damit steht die neue Spalte zwischen „Zusätzlicher Spleiß“ und den Stunden,
und beide behalten die volle Breite. Der neu gesetzte Kopf der Stundenspalte
trägt den LV-Wortlaut „Normalstunde Monteur Glasfaser“; der Zusatz „(bei
Problemen, in Absprache)“ aus dem Original bleibt erhalten.

Die dafür nötigen Linienmaße sind aus den Vorlagen bei 2000 dpi abgenommen
(Zeilentrenner 0,504 bzw. 0,612 pt, Ränder 0,972 bzw. 1,224 pt), damit die
neu gezogenen Linien nicht von den gedruckten abweichen. Genauso wurden die
vier überschriebenen Positionsnummern vermessen: Grundlinie, Mitte und
Schriftgröße stammen aus der Tinte der gedruckten Nummer, damit die neue
exakt an ihrer Stelle sitzt.

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
| `vorlage/Muster_TB.pdf` | Tiefbau-Blatt, wie geliefert (ausgefüllt) |
| `vorlage/Blanko_TB.pdf` | Tiefbau-Blatt geleert (steckt in `index.html`) |

## Zur Technik

Die Werte werden nicht in Formularfelder geschrieben – das Blatt hat keine.
Sie werden als Text auf die Originalseite gesetzt, an aus den Gitterlinien
gemessenen Koordinaten. Nur die drei vorgedruckten Angaben Ort/Datum,
Unternehmen und BV werden vorher weiß überdeckt; die Linien darunter bleiben
stehen.

Das Tiefbau-Blatt ist A4 hoch ohne Seitendrehung und braucht keine
Umrechnung. Die beiden Querformat-Vorlagen dagegen sind um 90° gedrehte
Seiten; für das Werkzeug wurden sie einmalig auf echtes Querformat
normalisiert
(`vorlage/*_quer.pdf`): Seitendrehung entfernt, MediaBox getauscht und
die Transformation `0 -1 1 0 0 595.22 cm` an den Anfang des Inhaltsstroms
gestellt. Der Inhalt ist unverändert – „Albachten“ liegt vorher wie nachher
auf (184,0 | 83,7). Dadurch entsprechen die gemessenen Zellkoordinaten
direkt den PDF-Koordinaten, und im Browser genügt
`y_pdf = 595,22 − y_gemessen` ohne Rotationsmatrix.
