# KYL Landingpage — Richtung „Serviceheft"

Einseitige Landingpage. Reines HTML, CSS und JavaScript, keine Abhängigkeiten,
kein Build-Schritt, keine externen Requests.

```
landingpage/
├── index.html      Die Seite
├── css/style.css   Das Gestaltungssystem
├── js/main.js      Menü, Formular, Jahreszahl
├── fonts/          Instrument Sans und JetBrains Mono, selbst gehostet
├── img/            Belegfotos, siehe img/README.md
└── DESIGN.md       Design-System für Stitch, aus der Primefold-Referenz
                    abgeleitet. Die Seite folgt ihm bewusst nicht, siehe unten.
```

## Warum diese Richtung

Der erste Entwurf folgte `DESIGN.md` und damit der Primefold-Referenz: dunkler
Foto-Hero, zweizeilige Headline, Pillen-Buttons, Dreierraster aus Karten,
nummerierte Schritte, dunkles Abschlussband. Die Referenz trägt das, weil sie
exzellente Fotografie hat. Ohne Fotos blieb das Skelett übrig, und das Skelett
ist die Vorlage, die derzeit jede zweite Dienstleisterseite benutzt.

Die zweite Fassung holt die Gestaltung aus der Sache selbst. Gebäudebetreuung
heißt Turnus, Begehung, Abnahme, Objektakte. Die Seite ist deshalb gesetzt wie
ein gepflegtes Serviceheft.

## Die Mittel

| Mittel | Umsetzung |
|---|---|
| Raster | Schmale Randspalte mit Sektionsnummer, breite Inhaltsspalte |
| Struktur | Haarlinien, keine Karten, keine runden Ecken, keine Schatten |
| Leistungen | Tabelle mit Nummer, Leistung und üblichem Turnus |
| Zahlen | Tabellenschrift, weil Turnus und Jahreszahlen hier Daten sind |
| Bilder | Belege mit Nummer und Bildunterschrift, nicht ganzflächig |
| Farbe | Papierweiß, Tinte, das Markenblau. Dieselbe Skala wie `kyl/` |
| Schrift | Instrument Sans für Text, JetBrains Mono für Zahlen |
| Bewegung | Nur Lesestand: mitlaufende Randspalte, Registermarken, abgehakte Zeilen |

Zwei Regeln aus den Skills berühren sich hier: Tabellenschrift für kleine
Beschriftungen gilt als Merkmal generierter Seiten. Sie ist hier trotzdem
richtig, weil sie ausschließlich auf echten Daten liegt, nie auf Dekoration.

## Farbskala

Beide Auftritte teilen sich eine Skala. Die Werte stehen in
`css/style.css` unter `:root`.

| Rolle | Wert |
|---|---|
| Papier | `#FFFFFF` |
| Abgesetzte Bahn | `#F4F4F5` |
| Text | `#14161A` |
| Beschriftung, Fließtext | `#6B6F76` |
| Haarlinie | `#E6E7EA` |
| Starke Linie | `#14161A` |
| Feldrahmen | `#86898F` |
| Akzent (Flächen, Fokus) | `#0071E3` |
| Akzent dunkel (Ziffern, Links) | `#005BB8` |
| Akzentfläche | `#E9F2FD` |

Zwei Entscheidungen dahinter, beide aus der Kontrastrechnung:

- **Es gibt keine dritte, hellere Textstufe.** Ein Grau, das heller als
  `#6B6F76` ist, hält auf der abgesetzten Bahn die 4,5:1 nicht mehr. Die
  Abstufung kommt deshalb aus Größe und Gewicht, nicht aus einem dritten Ton.
- **Kleine Ziffern und Links laufen im dunklen Blau.** `#0071E3` erreicht auf
  der Bahn nur 4,27:1. Das helle Blau bleibt Flächen, Rahmen und dem
  Fokusring vorbehalten, wo 3:1 genügt.

## Scrolleffekte

Vier Stück, alle aus der Dokument-Metapher heraus. Keines ist das übliche
Einblenden von unten, das in allen drei Skills als Merkmal generierter Seiten
gilt.

| Effekt | Was passiert | Technik |
|---|---|---|
| Mitlaufende Randspalte | Nummer und Bezeichnung des Abschnitts bleiben neben dem Inhalt stehen, bis der nächste sie wegschiebt | `position: sticky`, reines CSS |
| Registermarken | Reiter am rechten Rand wie bei einer Mappe, der aktuelle färbt sich und zeigt seine Bezeichnung | `IntersectionObserver` |
| Abgehakte Zeilen | Jede Zeile des Leistungsverzeichnisses bekommt beim Vorbeiscrollen einmalig ein Häkchen, leicht versetzt | `IntersectionObserver`, `opacity` und `transform` |
| Aktenkopf | Keine Bewegung, aber der Punkt, der den Charakter am deutlichsten hebt: Feldbezeichnung über dem Wert, Haarlinien als Zellgrenzen | CSS-Raster |

Die Registermarken brauchen freien Seitenrand. Unter 1200 px sind sie
ausgeblendet, zwischen 1200 und 1400 px zeigen sie nur die Nummer.

Bei `prefers-reduced-motion` entfallen die Übergänge, die Zustände bleiben:
sie tragen Information, keine Dekoration. Ohne JavaScript sind alle Häkchen
sofort sichtbar und die Reiter funktionieren als gewöhnliche Ankerlinks.

## Lokal ansehen

```bash
python3 -m http.server 8000     # im Repository-Wurzelverzeichnis
# dann http://localhost:8000/landingpage/
```

## Vorschau zum Weitergeben

```bash
python3 landingpage/build-preview.py
```

Erzeugt zwei Dateien, die nichts nachladen: Stylesheet, Skript und die vier
Schriftdateien stecken als `data:`-URI in der Datei selbst.

| Datei | Wofür |
|---|---|
| `preview.html` | Zum Doppelklicken oder Verschicken. Läuft ohne Server |
| `preview-artifact.html` | Fassung ohne Dokumentgerüst, für die Veröffentlichung als Artifact |

Beide sind erzeugt und stehen in `.gitignore`. Nach jeder Änderung an der
Seite das Skript erneut laufen lassen.

Was in der Vorschau fehlt: Impressum und Datenschutz liegen in `../kyl/` und
sind aus der eigenständigen Datei heraus nicht erreichbar.

## Verhältnis zur Website in `kyl/`

Zwei getrennte Auftritte für dasselbe Unternehmen. `kyl/` ist die vollständige
Website mit Impressum und Datenschutz, hierher verlinkt die Fußzeile. Soll die
Landingpage die Website ersetzen, ist das ein Verschiebe-Vorgang plus das
Mitnehmen der beiden Rechtsseiten.

## Noch zu erledigen

- [ ] **Belegfotos** nach `img/`, Dateinamen in `img/README.md`. Diese
      Gestaltung trägt auch ohne Fotos, mit echten Aufnahmen wird sie
      glaubwürdiger
- [ ] **Turnus-Angaben prüfen.** Im Leistungsverzeichnis stehen die üblichen
      Intervalle, die wir angenommen haben. Wenn sie nicht stimmen, sind sie
      falsche Zusagen und müssen korrigiert werden
- [ ] **Formular-Backend** anbinden: `js/main.js`, Block 2, TODO im
      Submit-Handler
