# Gestaltungsnotizen

Kurzes Gedächtnis für spätere Durchgänge: was entschieden wurde und warum.

## Gesetzt durch den Kunden

Diese Punkte stammen aus der vom Kunden geschickten Vorlage und seiner
ausdrücklichen Wahl. Sie stehen nicht zur Diskussion, auch wenn einzelne davon
in Gestaltungsratgebern als Allerweltslösung gelten:

- zweite Headline-Zeile kursiv und in der Akzentfarbe
- Versalien-Labels als Pille über den Abschnitten „Leistungen" und „Arbeiten"
- Foto-Hero mit runden Ecken und Verlauf nach links
- Pillen-Buttons mit rundem Pfeil-Kreis
- Kennzahlenband unter dem Hero
- Blau `#0071e3` als einzige Akzentfarbe

## Bewusst geändert (Durchgang 2)

| Vorher | Jetzt | Grund |
|---|---|---|
| Einblenden von unten bei 22 Elementen | Ein Aufbau des Heros beim Laden | Bewegung auf jedem Abschnitt liest sich wie eine Vorlage und hält den Leser auf |
| Karten schweben und werfen Schatten beim Überfahren | Karten liegen ruhig | Sie sind Inhalt, kein Bedienelement. Bewegung antwortet auf Handlungen |
| Ein Radius für alles (22 px) | Vier Stufen: 10 / 16 / 22 / 28 px | Der Radius bildet jetzt Hierarchie ab statt Einheitsbrei |
| Pfeil-Badge auf den Leistungskarten | Nur noch auf den Projektkacheln | Ein Pfeil verspricht ein Ziel. Die Karten verlinken nichts |
| Vier Labels über Überschriften | Zwei | „Über uns" und „Kontakt" standen über Überschriften, die dasselbe sagen |
| `A · B · C` in der Fußzeile | Adressblock mit echten Zeilen | Mittelpunkt-Ketten sind Zierrat, kein Aufbau |
| Bewertungszeile „5,0 ★★★★★" | „Gebäudedienstleistungen aus Greven, seit 2024" | Ohne echte Bewertungen wäre das eine erfundene Tatsachenbehauptung und wettbewerbsrechtlich angreifbar |
| Kennzahlenband mit vier Werten | Drei | „[X] Std. bis zur Rückmeldung" war frei erfunden |

## Durchgang 3: Prüfung mit ui-ux-pro-max

Gegen die UX-Regeln des Skills geprüft. Zwei echte Befunde, beide behoben:

- **Klickflächen in der Fußzeile waren 22 px hoch.** WCAG 2.2 verlangt
  mindestens 24 px für eigenständige Links. Jetzt 32 px durch Innenabstand.
  Der Link „Datenschutzerklärung" mitten im Satz bleibt kleiner, für Links
  im Fließtext sieht die Regel eine Ausnahme vor.
- **Bewegungsdauern waren über die Datei verstreut** (0.2 bis 0.7 s, frei
  gegriffen). Jetzt drei Tokens: `--dur-fast`, `--dur-base`, `--dur-slow`.

Nicht übernommen wurde der Farb- und Schriftvorschlag des Skills (Blau mit
Orange, Poppins mit Open Sans). Das ist die Allerweltslösung für
Dienstleister-Seiten und würde die Entscheidung des Kunden überschreiben.

## Durchgang 4: Prüfung mit taste-skill

Ein Regelwerk gegen schablonenhafte Oberflächen. Es setzt React, Next.js und
Tailwind voraus, deshalb greift nur der Gestaltungsteil. Die Seite erfüllt ihn
bis auf einen Punkt:

- **Geviertstriche `—` im Fließtext.** Sieben Stellen ersetzt, je nach Satz
  durch Doppelpunkt, Komma oder einen eigenen Satz. Im Deutschen wäre ohnehin
  der Halbgeviertstrich `–` richtig, der Geviertstrich ist englische
  Typografie. Die Änderung ist also unabhängig vom Skill korrekt.

Nicht übernommen: Dunkelmodus als Pflicht (eine regionale Dienstleisterseite
braucht kein zweites Farbschema), die Schriftvorschläge und die
Bewegungsmuster mit GSAP. Begründung in `.claude/skills/taste-skill/HERKUNFT.md`.

## Offen

- `[ANZAHL]+ Betreute Objekte` ist der letzte Platzhalter im Kennzahlenband.
  Liegt keine Zahl vor, ersatzlos streichen statt schätzen.
- Ohne echte Fotos bleibt diese Gestaltung halbfertig. Das ist der größte
  offene Punkt, nicht die Gestaltung selbst.
- Kommen später Unterseiten je Leistung dazu, gehört das Pfeil-Badge zurück
  auf die Leistungskarten — dann stimmt das Versprechen wieder.
