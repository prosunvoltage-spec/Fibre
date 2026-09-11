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
| Farbe | Papierweiß, Tinte, eine Stempelfarbe `#1D3FA0` für Nummern und Status |
| Schrift | Instrument Sans für Text, JetBrains Mono für Zahlen |
| Bewegung | Keine. Ein Protokoll bewegt sich nicht beim Lesen |

Zwei Regeln aus den Skills berühren sich hier: Tabellenschrift für kleine
Beschriftungen gilt als Merkmal generierter Seiten. Sie ist hier trotzdem
richtig, weil sie ausschließlich auf echten Daten liegt, nie auf Dekoration.

## Lokal ansehen

```bash
python3 -m http.server 8000     # im Repository-Wurzelverzeichnis
# dann http://localhost:8000/landingpage/
```

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
