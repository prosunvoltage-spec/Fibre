# Herkunft

Dieser Skill stammt aus dem öffentlichen Repository
[nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill),
Version 2.13.0, Stand Commit `7f69fed`. Lizenz: MIT, Text in `LICENSE`.

Übernommen wurde der Ordner `.claude/skills/ui-ux-pro-max` unverändert, bis auf
eine Auslassung: `scripts/tests/` ist nicht dabei. Die Tests gehören zur
Entwicklung des Skills und werden zur Nutzung nicht gebraucht.

## Was er kann

Eine durchsuchbare Datenbank mit UI- und UX-Wissen: 119 UX-Richtlinien,
192 Farbpaletten, 74 Schriftpaarungen, 79 Stile, 25 Diagrammtypen,
22 Technologie-Stacks. Abfrage über ein Python-Skript ohne Abhängigkeiten:

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "touch target size" --domain ux
```

## Prüfung vor der Aufnahme

Die beiden Laufzeit-Skripte `search.py` und `core.py` wurden gelesen und auf
Netzwerkzugriffe, Schreiboperationen, Unterprozesse und dynamische Auswertung
geprüft. Nichts davon ist enthalten: die Skripte lesen nur die mitgelieferten
Daten und geben Text aus.

## Einordnung

Die Empfehlungen zu Farbe und Schrift fallen erfahrungsgemäß
Allerweltslösungen zu (Blau mit Orange, Poppins mit Open Sans). Stark ist der
Skill bei den überprüfbaren Regeln: Klickflächen, Kontraste, Formularfehler,
Bewegung, Navigationsmuster. Als Prüfliste taugt er, als Geschmacksgeber
weniger.
