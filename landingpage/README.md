# KYL Landingpage

Einseitige Landingpage, gebaut nach `DESIGN.md`. Reines HTML, CSS und
JavaScript, keine Abhängigkeiten, kein Build-Schritt, keine externen Requests.

```
landingpage/
├── DESIGN.md       Design-System, aus der Primefold-Referenz abgeleitet
├── index.html      Die Seite
├── css/style.css   Umsetzung des Design-Systems
├── js/main.js      Menü, Karussell, Formular
├── fonts/          Hanken Grotesk, selbst gehostet
└── img/            Fotos, siehe img/README.md
```

## Lokal ansehen

```bash
python3 -m http.server 8000     # im Repository-Wurzelverzeichnis
# dann http://localhost:8000/landingpage/
```

## Aufbau der Seite

Die Sektionsformen wechseln durchgehend, keine zwei benachbarten Abschnitte
sehen gleich aus:

1. **Hero** — Foto als Fläche, gerichteter Verlauf von links, Text auf der
   dunklen Seite, Leistungs-Chips an der Unterkante
2. **Versprechenszeile** — vier Aussagen, ruhig gesetzt. Hier stünden bei der
   Referenz Kundenlogos. KYL hat noch keine, erfundene wären wertlos
3. **Ablauf** — vier Schritte auf einer großen Fläche. Die Nummern sind
   zulässig, weil es wirklich eine Abfolge ist
4. **Leistungen** — sechs Karten, drei Spalten
5. **Arbeiten** — Karussell, die Nachbarn bleiben angeschnitten sichtbar
6. **Über uns** — zweispaltig, Bild und Text
7. **Abschlussband** — dunkle Fläche mit großem Radius
8. **Kontakt** — Formular und Kontaktdaten
9. **Fußzeile**

## Bewegung

Genau zwei Stellen: Der Hero baut sich beim Laden einmal auf, versetzt um
90 Millisekunden je Element. Alles andere antwortet auf eine Handlung, also
Karussell, Menü, Fokus, Überfahren. Kein Einblenden beim Scrollen.
`prefers-reduced-motion` schaltet den Hero-Aufbau ab.

## Verhältnis zur Website in `kyl/`

Zwei getrennte Auftritte für dasselbe Unternehmen. `kyl/` ist die vollständige
Website mit Impressum und Datenschutz, diese Landingpage ist die verdichtete
Fassung nach der neuen Referenz. Impressum und Datenschutz verlinken von hier
nach `../kyl/`.

Soll die Landingpage die Website ersetzen, ist das ein Verschiebe-Vorgang plus
das Mitnehmen der beiden Rechtsseiten. Sag Bescheid, dann mache ich das.

## Noch zu erledigen

- [ ] **Echte Fotos** nach `img/`, Dateinamen in `img/README.md`. Diese
      Gestaltung lebt vom Hero-Foto, die Farbfläche ist nur ein Notbehelf
- [ ] **Formular-Backend** anbinden: `js/main.js`, Block 3, TODO im
      Submit-Handler
- [ ] Impressum und Datenschutz verlinken nach `../kyl/`. Wird die
      Landingpage eigenständig veröffentlicht, brauchen beide eine eigene Kopie
