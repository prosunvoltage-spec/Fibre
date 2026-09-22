"""Traegt Aufmassdaten in das Original-Blanko-PDF ein.

Das Blatt wird nicht neu gezeichnet: die Originalseite bleibt unveraendert
(Logo, Tabelle, Ueberschriften, Unterschriftsfelder) - die eingegebenen Werte
werden als Text darueber gesetzt.

Die Vorlage ist eine um 90 Grad gedrehte Seite. Alle Koordinaten in layout.py
sind im *angezeigten* Querformat (842 x 595 pt) gemessen; hier werden sie mit
der Derotationsmatrix der Seite in deren interne Koordinaten umgerechnet.
"""
import pymupdf

from layout import (ANZEIGE, COLS, KOPFFELDER, MAX_ROWS, TAETIGKEITEN,
                    X_NVT, X_TAETIGKEIT, row_rect)

REGULAR = "helv"
BOLD = "hebo"
WEISS = (1, 1, 1)

# Taetigkeit per ASCII-Name *und* per Anzeigename (mit Umlauten) auffindbar
BY_NAME = {t["name"]: t for t in TAETIGKEITEN}
BY_NAME.update({ANZEIGE.get(t["name"], t["name"]): t for t in TAETIGKEITEN})


def _zentriert(page, zelle, text, size, bold=False):
    """Schreibt text mittig in die Zelle (Angabe im Querformat-System)."""
    if not text:
        return
    font = BOLD if bold else REGULAR
    x0, y0, x1, y1 = zelle
    nutzbar = x1 - x0 - 2.0
    while size > 3.4 and pymupdf.get_text_length(text, font, size) > nutzbar:
        size -= 0.2

    # Kasten um die Zellenmitte, hoch genug fuer eine Zeile dieser Schriftgroesse
    mitte = (y0 + y1) / 2.0
    kasten = pymupdf.Rect(x0 + 1.0, mitte - size * 0.92,
                          x1 - 1.0, mitte + size * 0.92)
    page.insert_textbox(kasten * page.derotation_matrix, text,
                        fontname=font, fontsize=size,
                        align=pymupdf.TEXT_ALIGN_CENTER, rotate=90)


def _menge_formatieren(menge):
    """1250 -> '1250', 340.5 -> '340,5' (deutsches Dezimalkomma)."""
    if menge is None:
        return ""
    if isinstance(menge, str):
        menge = menge.strip().replace(",", ".")
        if not menge:
            return ""
        try:
            menge = float(menge)
        except ValueError:
            return str(menge)
    if isinstance(menge, float):
        if menge.is_integer():
            return str(int(menge))
        return f"{menge:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(menge)


def fuellen(vorlage, ziel, kopf, zeilen):
    """Erzeugt das ausgefuellte Aufmassblatt.

    kopf:   dict mit den Schluesseln aus layout.KOPFFELDER
    zeilen: Liste von dicts mit nvt / taetigkeit / menge / bemerkung
    """
    if len(zeilen) > MAX_ROWS:
        raise ValueError(
            f"Das Aufmassblatt hat {MAX_ROWS} Zeilen, es wurden "
            f"{len(zeilen)} Positionen eingetragen. Bitte auf mehrere "
            f"Blaetter aufteilen.")

    doc = pymupdf.open(vorlage)
    page = doc[0]

    for schluessel, feld in KOPFFELDER.items():
        wert = str(kopf.get(schluessel) or "").strip()
        x0, x1, y = feld["box"]
        if feld["clear"]:
            # vorgedruckten Wert ueberdecken, die Linie darunter bleibt stehen
            weg = pymupdf.Rect(x0, y - 9.0, x1, y - 0.6)
            page.draw_rect(weg * page.derotation_matrix, color=None, fill=WEISS)
        _zentriert(page, (x0, y - 9.0, x1, y - 0.6), wert, 6.8, bold=True)

    for i, z in enumerate(zeilen, start=1):
        name = str(z.get("taetigkeit") or "").strip()
        eintrag = BY_NAME.get(name)
        if eintrag is None:
            bekannt = "\n  - ".join(ANZEIGE.get(t["name"], t["name"])
                                    for t in TAETIGKEITEN)
            raise ValueError(
                f"Zeile {i}: unbekannte Taetigkeit {name!r}.\n"
                f"Erlaubt sind:\n  - {bekannt}")

        _zentriert(page, row_rect(i, *X_NVT),
                   str(z.get("nvt") or "").strip(), 6.2)

        text = ANZEIGE.get(eintrag["name"], eintrag["name"])
        bemerkung = str(z.get("bemerkung") or "").strip()
        if bemerkung:
            text = f"{text} ({bemerkung})"
        _zentriert(page, row_rect(i, *X_TAETIGKEIT), text, 6.2)

        _zentriert(page, row_rect(i, *COLS[eintrag["col"]]),
                   _menge_formatieren(z.get("menge")), 6.4, bold=True)

    doc.save(ziel, garbage=3, deflate=True)
    doc.close()
    return ziel
