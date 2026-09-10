# KYL Facility Management & Services — Website

One-Page-Website im Apple-Stil für KYL Facility Management & Services (Greven).
Reines HTML/CSS/JS, keine Abhängigkeiten, kein Build-Schritt.

## Struktur

```
kyl/
├── index.html          One-Pager: Hero, Vertrauensleiste, Services, Projekte,
│                       Über uns, CTA, Kontakt, Footer
├── impressum.html      Pflichtangaben nach § 5 DDG
├── datenschutz.html    Datenschutzerklärung
├── css/style.css       Design-System, alle Styles (mobile-first)
├── js/main.js          Nav-Scroll-State, Mobile-Menü, Scroll-Reveal, Formular
└── img/                Fotos (siehe img/README.md)
```

## Lokal ansehen

```bash
python3 -m http.server 8000
# dann http://localhost:8000/kyl/ aufrufen
```

## Design-System

Alle Werte stehen als Custom Properties oben in `css/style.css` unter `:root`:

- **Akzentfarbe** `--c-accent: #0071e3` (Hover `#0055b8`) — an einer Stelle änderbar
- **Basis** `--c-bg: #fafafa`, Text `--c-dark: #1d1d1f`
- **Spacing** 8-Punkt-System `--s-1` bis `--s-16`
- **Container** `--container: 1200px`
- **Schrift** Systemfont-Stack (SF Pro / Segoe UI / Inter), keine Webfont-Downloads

Breakpoints: 700px (2 Spalten), 900px (Desktop-Navi, zweispaltige Sektionen),
1024px (3 Spalten).

## Noch zu erledigen

- [ ] **Straße und Hausnummer** in `impressum.html` und `datenschutz.html` ergänzen
      (aktuell `[Straße und Hausnummer]`) — ohne vollständige Anschrift ist das
      Impressum nicht rechtssicher
- [ ] **USt-IdNr.** und **Registernummer** in `impressum.html` eintragen
      (stehen aktuell als „wird nachgereicht“)
- [ ] **Echte Fotos** nach `img/` legen, Dateinamen siehe `img/README.md`
- [ ] **Formular-Backend** anbinden: `js/main.js`, Block 4, TODO-Kommentar im
      Submit-Handler (Formspree, Netlify Forms oder eigenes Backend)
- [ ] Datenschutzerklärung rechtlich prüfen lassen, sobald externe Dienste
      (Formular-Backend, Karte, Analytics) eingebunden sind

Bereits eingepflegt sind Telefon, E-Mail, Ort, Inhaber und der Instagram-Link.

## Erweitern

Für eine eigene Unterseite `impressum.html` kopieren: Header, Footer und die
Klasse `site-header--solid` sind dort bereits so aufgebaut, dass nur der Inhalt
zwischen `<main>` und `</main>` ausgetauscht werden muss.

## Barrierefreiheit & Performance

Semantische Landmarks, Skip-Link, sichtbarer Fokus-Ring, Alt-Texte an allen
Bildern, `aria-expanded` am Menü-Button, Live-Regionen an den Formularfehlern.
Animationen respektieren `prefers-reduced-motion`. Keine externen Requests:
Icons sind inline, Schriften kommen vom System, Bilder laden `lazy`.
