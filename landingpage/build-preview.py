#!/usr/bin/env python3
"""Baut aus index.html, css/style.css, js/main.js und den Schriftdateien
eine einzige, in sich geschlossene HTML-Datei fuer die Vorschau.

    python3 build-preview.py

Ergebnis: preview.html im selben Ordner. Die Datei laedt nichts nach,
Schriften stecken als data-URI im Stylesheet. Fuer Artifacts wird
zusaetzlich preview-artifact.html geschrieben: derselbe Inhalt, aber ohne
doctype, html-, head- und body-Tags, weil die Artifact-Umgebung die selbst
setzt.
"""

import base64
import pathlib
import re

hier = pathlib.Path(__file__).parent


def schriften_inline(faces_css: str) -> str:
    """Ersetzt jede url('../fonts/x.woff2') durch ein data-URI."""
    def ersetze(treffer):
        name = treffer.group(1)
        daten = (hier / "fonts" / name).read_bytes()
        b64 = base64.b64encode(daten).decode("ascii")
        return f"url('data:font/woff2;base64,{b64}')"

    return re.sub(r"url\('\.\./fonts/([^']+)'\)", ersetze, faces_css)


def baue():
    html = (hier / "index.html").read_text(encoding="utf-8")
    css = (hier / "css" / "style.css").read_text(encoding="utf-8")
    js = (hier / "js" / "main.js").read_text(encoding="utf-8")
    faces = (hier / "fonts" / "faces.css").read_text(encoding="utf-8")

    # Der Import wird durch die Schriftdefinitionen mit data-URI ersetzt
    css = css.replace('@import url("../fonts/faces.css");', schriften_inline(faces))

    # Stylesheet-Link raus, Stile rein
    html = re.sub(
        r'  <link rel="preload"[^>]*>\n  <link rel="stylesheet" href="css/style\.css">',
        "  <style>\n" + css + "\n  </style>",
        html,
    )

    # Skript einbetten
    html = html.replace(
        '  <script src="js/main.js" defer></script>',
        "  <script>\n" + js + "\n  </script>",
    )

    # Rechtsseiten liegen im Nachbarordner und sind aus der Vorschau heraus
    # nicht erreichbar. Der Hinweis steht in der Uebergabe.
    (hier / "preview.html").write_text(html, encoding="utf-8")

    # Fassung fuer Artifacts: nur der Inhalt, das Geruest setzt die Umgebung
    inhalt = html
    inhalt = inhalt[inhalt.index("<title>"):]
    inhalt = inhalt.replace("</head>\n<body>\n", "", 1)
    inhalt = inhalt.replace("</body>\n</html>\n", "", 1)
    # Die Metaangaben des Dokumentkopfs gehoeren nicht in den Rumpf
    inhalt = re.sub(r'\n  <meta[^>]*>', "", inhalt)
    (hier / "preview-artifact.html").write_text(inhalt, encoding="utf-8")

    for datei in ("preview.html", "preview-artifact.html"):
        groesse = (hier / datei).stat().st_size
        print(f"{datei}: {groesse/1024:.0f} KB")


if __name__ == "__main__":
    baue()
