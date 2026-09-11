# KYL Facility Management & Services — Website

One-Page-Website für KYL Facility Management & Services (Greven).
Reines HTML/CSS/JS, keine Abhängigkeiten, kein Build-Schritt, keine externen
Requests.

## Struktur

```
kyl/
├── index.html          One-Pager: Hero, Kennzahlen, Leistungen, Arbeiten,
│                       Über uns, CTA, Kontakt, Footer
├── impressum.html      Pflichtangaben nach § 5 DDG
├── datenschutz.html    Datenschutzerklärung
├── css/style.css       Design-System und alle Styles (mobile-first)
├── js/main.js          Navi-Zustand, Mobile-Menü, Scroll-Reveal, Formular
├── fonts/              Hanken Grotesk, selbst gehostet (siehe fonts/README.md)
├── img/                Fotos (siehe img/README.md)
└── design/             Entwürfe der drei Gestaltungsrichtungen
```

## Lokal ansehen

```bash
python3 -m http.server 8000
# dann http://localhost:8000/kyl/ aufrufen
```

## Design-System

Umgesetzt ist Richtung C aus `design/`: helle Flächen, Foto-Hero mit runden
Ecken, Pillen-Buttons mit Pfeil-Kreis, Karten mit rundem Pfeil-Badge. Die
Signatur ist die zweite Headline-Zeile in Kursiv.

Alle Werte stehen als Custom Properties oben in `css/style.css` unter `:root`:

| Token | Wert |
|---|---|
| `--c-accent` | `#0071e3`, dunkler `#005bb8` |
| Flächen | `--c-white` `#ffffff`, `--c-surface` `#f4f4f5` |
| Text | `--c-text` `#14161a`, `--c-text-soft` `#6b6f76` |
| Linien | `--c-line` `#e6e7ea`, `--c-line-strong` `#14161a`, `--c-line-input` `#86898f` |
| Radien | 10 px Felder, 16 px Karten, 22 px Kacheln, 28 px Hero, Pillen rund |
| Spacing | 8-Punkt-System `--s-1` bis `--s-12` |
| Container | `--container` 1360 px |

Breakpoints: 700 px (zwei Spalten), 900 px (zweispaltige Sektionen),
1000 px (Desktop-Navi), 1024 px (drei Spalten).

Wiederkehrende Bausteine: `.pill` (vier Varianten), `.eyebrow`, `.card`,
`.tile`, `.badge-arrow`, `.check-list`. Neue Abschnitte sollten diese
Bausteine nutzen, statt eigene Muster einzuführen.

## Noch zu erledigen

- [ ] **Straße und Hausnummer** in `impressum.html` und `datenschutz.html`
      ergänzen (aktuell `[Straße und Hausnummer]`) — ohne vollständige
      Anschrift ist das Impressum nicht rechtssicher
- [ ] **USt-IdNr.** und **Registernummer** in `impressum.html` eintragen
- [ ] **Drei Zahlen im Markup** ersetzen, alle mit `PLATZHALTER` kommentiert:
      Anzahl betreuter Objekte, übliche Reaktionszeit, Anzahl der Bewertungen
      in der Hero-Zeile. Solange keine echten Werte vorliegen, lieber die
      betroffenen Elemente entfernen als Zahlen erfinden
- [ ] **Echte Fotos** nach `img/` legen, Dateinamen siehe `img/README.md`.
      Diese Gestaltung lebt von Fotos — die Farbflächen sind nur ein Notbehelf
- [ ] **Formular-Backend** anbinden: `js/main.js`, Block 4, TODO im
      Submit-Handler (Formspree, Netlify Forms oder eigenes Backend)
- [ ] Datenschutzerklärung prüfen lassen, sobald externe Dienste dazukommen

Eingepflegt sind Telefon, E-Mail, Ort, Inhaber und der Instagram-Link.

## Barrierefreiheit & Performance

Semantische Landmarks, Skip-Link, sichtbarer Fokus-Ring, Alt-Texte an allen
Bildern, `aria-expanded` am Menü-Button, Live-Regionen an den Formularfehlern.
Alle Text-Hintergrund-Paare liegen über 4,5:1, Feldrahmen und Fokusring über
3:1. Die Landingpage in `landingpage/` nutzt dieselbe Skala.

Bewegung gibt es an drei Stellen: der Hero baut sich beim Laden einmal auf,
Bedienelemente antworten auf Überfahren und Klick, und der Kopf zeigt den
Lesestand. Kein Einblenden beim Scrollen.

Der Lesestand besteht aus zwei Teilen: einem laufenden Kolumnentitel neben dem
Logo, der den aktuellen Abschnitt nennt, und einer Haarlinie an der Unterkante
des Kopfes, die den Fortschritt der Seite zeigt. Die Navigation markiert
denselben Abschnitt, damit sich nicht zwei Anzeigen widersprechen. Unter
1000 px übernimmt das Menü die Orientierung. `prefers-reduced-motion` schaltet den Hero-Aufbau ab. Die
Begründungen für diese und weitere Entscheidungen stehen in
`design/NOTIZEN.md`.

Keine externen Requests: Icons sind inline, die Schrift liegt lokal, Bilder
laden `lazy`. Die vier Schriftdateien wiegen zusammen rund 78 KB.
