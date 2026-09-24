# Wissensbasis (`/knowledge/`)

Alle **maßgeblichen Fach- und Regelwerksinhalte** liegen hier. Die Software
greift ausschließlich auf Dokumente zu, die in diesem Ordner tatsächlich
vorhanden sind — nichts wird aus Modell-Wissen ergänzt.

## Struktur

```
/knowledge/
├── rsa21/               # RSA 21 – Richtlinien für die Sicherung von Arbeitsstellen
├── stvo/                # StVO-Ausschnitte, sofern relevant
├── vwv_stvo/            # VwV-StVO
├── ztv_sa/              # ZTV-SA
├── mvas/                # MVAS 1999
├── regelplaene/         # ← Regelplan-Bibliothek (siehe regelplaene/README.md)
├── referenzfaelle/      # ← Referenz-NVT aus historischen VRAs
└── lokale_vorgaben/     # ← Vorgaben einzelner Straßenverkehrsbehörden
```

## Was hier hineinkommt (Fachanwender-Verantwortung)

- **Original-Regelwerke** als PDF, mit klarer Versionsangabe
- **Vom Auftraggeber freigegebene Regelpläne** als PDF + `metadata.json`
- **Behördliche Standard-Auflagen** (z.B. Stadt Münster) als strukturierte JSON

## Was hier NIEMALS hineingehört

- Frei erfundene Werte
- Aus dem LLM „übernommene" Regeln ohne Original-Quelle
- Rechtsauslegungen ohne Rückverweis auf ein reales Dokument

## Was ins Git kommt und was nicht

`.gitignore` schließt Binärdateien (`*.pdf`, `*.png`, `*.jpg`) unter
`/knowledge/` aus. **Getrackt sind nur die Metadaten** (`*.json`, `*.md`).
Binärdateien werden per Extraktionsskript aus der Referenz-PDF erzeugt und
liegen lokal in der jeweiligen Arbeitsumgebung.

Grund: die Binaries können personenbezogen (Fotos), urheberrechtlich
geschützt (RSA-Zeichnungen) oder behördlich vertraulich sein. Deshalb keine
Verteilung über das Repo, sondern reproduzierbare Extraktion aus der
Original-PDF.
