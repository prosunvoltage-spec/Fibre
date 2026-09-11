# Schriften

**Hanken Grotesk** von Alfredo Marco Pradil, lizenziert unter der
[SIL Open Font License 1.1](https://openfontlicense.org). Die Lizenz erlaubt
das Selbsthosten ausdrücklich.

Die Dateien liegen hier lokal, statt sie von Google Fonts zu laden. Zwei Gründe:

1. **Datenschutz.** Beim Laden von `fonts.googleapis.com` geht die IP-Adresse
   jedes Besuchers an Google. Deutsche Gerichte haben das ohne Einwilligung
   als Verstoß gegen die DSGVO gewertet.
2. **Tempo.** Kein zusätzlicher DNS-Lookup und keine dritte Verbindung.

Es sind variable Schriftdateien: eine Datei deckt alle Gewichte von 100 bis 900
ab. Vier Dateien, zusammen rund 78 KB.

| Datei | Schnitt |
|---|---|
| `hankengrotesk-latin.woff2` | aufrecht, Latin |
| `hankengrotesk-latin-ext.woff2` | aufrecht, Latin erweitert |
| `hankengrotesk-italic-latin.woff2` | kursiv, Latin |
| `hankengrotesk-italic-latin-ext.woff2` | kursiv, Latin erweitert |

Eingebunden werden sie über `fonts/faces.css`, das `css/style.css` importiert.
