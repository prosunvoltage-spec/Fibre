# Musterbau GmbH – Website

Statische Website für ein allgemeines Bauunternehmen. Reines HTML/CSS/JS, keine Abhängigkeiten, keine Build-Schritte.

## Struktur

```
.
├── index.html          Startseite mit Leistungsübersicht
├── referenzen.html     Projekt-Galerie mit Filter
├── ueber-uns.html      Firmengeschichte, Werte, Team
├── kontakt.html        Kontaktformular, Adresse, Öffnungszeiten
├── css/style.css       Alle Styles (responsive, mobile-first)
├── js/main.js          Mobile-Menü, Filter, Formular-Validierung
└── img/                Bilder-Verzeichnis (aktuell leer, CSS-Gradients als Platzhalter)
```

## Lokal ansehen

Einfach `index.html` im Browser öffnen, oder:

```bash
python3 -m http.server 8000
# dann http://localhost:8000 aufrufen
```

## Anpassen

- **Firmenname / Kontaktdaten**: In allen `*.html` Dateien nach `Musterbau GmbH`, `Musterstraße`, `info@musterbau-gmbh.de` suchen und ersetzen
- **Farben**: Oben in `css/style.css` unter `:root` die Custom Properties `--color-primary` und `--color-accent` anpassen
- **Projekt-Bilder**: In `referenzen.html` die `.project-image`-Elemente ersetzen — statt `background:linear-gradient(...)` z.B. `background:url('img/projekt-01.jpg') center/cover`
- **Team-Fotos**: In `ueber-uns.html` die `.team-photo`-Divs durch `<img>` mit echten Fotos ersetzen
- **Formular-Backend**: `js/main.js` (Funktion `contactForm.addEventListener('submit', ...)`) sendet aktuell nichts an einen Server. Für den Live-Betrieb `fetch()` an ein Backend oder einen Service wie Formspree/Netlify Forms einbauen
- **Karte**: Im Kontaktbereich das `.map-placeholder`-Div durch einen `<iframe>` von Google Maps oder OpenStreetMap ersetzen

## Hinweise

- Alle Inhalte sind Platzhalter — vor dem Live-Gang durch echte Firmen-Daten ersetzen
- Impressum und Datenschutz-Seiten müssen für den deutschen Markt ergänzt werden (Pflicht!)
- Bilder sollten für Web optimiert werden (WebP, max. 200 KB pro Bild)
