"""
Layout-Definition des Blanko-Aufmassblatts (HK Albachten / HK Hiltrup West).

Alle Koordinaten sind in PDF-Punkten im *angezeigten* (gedrehten) Koordinaten-
system der Seite: 842 x 595 pt, Querformat, Ursprung oben links.
Sie wurden aus den Gitterlinien der Original-PDF gemessen.
"""

# --- Taetigkeitskatalog ------------------------------------------------------
# name: der Text, der im Excel-Dropdown und in der Spalte "Taetigkeit" steht
# pos:  Positionsnummer laut Leistungsverzeichnis
# unit: Einheit
# col:  Index der Mengenspalte im PDF (siehe COLS)
TAETIGKEITEN = [
    {"name": "Einblasen HK 24F",                      "pos": "02.02.01.02", "unit": "m",  "col": 0},
    {"name": "Einblasen HK 96F",                      "pos": "02.02.01.01", "unit": "m",  "col": 1},
    {"name": "GF-Kabel vorb. & Spleissen (bis 24F.)", "pos": "02.05.01.01", "unit": "St", "col": 2},
    {"name": "GF-Kabel vorb. & Spleissen (bis 96F.)", "pos": "02.05.01.02", "unit": "St", "col": 3},
    {"name": "Montage und Spleissen von Kopplern",    "pos": "02.05.01.03", "unit": "St", "col": 4},
    {"name": "Zusaetzliches Spleissen weiterer Fasern","pos": "02.05.01.04", "unit": "St", "col": 5},
    {"name": "GF ungespleisst ablegen",               "pos": "02.03.01.03", "unit": "m",  "col": 6},
    {"name": "Montieren EZA 12mm",                    "pos": "02.04.01.02", "unit": "St", "col": 7},
    {"name": "Stunden Monteur",                       "pos": "02.07.01.03", "unit": "h",  "col": 8},
]

# Umlaute/ss fuer die Anzeige im PDF und in Excel
ANZEIGE = {
    "GF-Kabel vorb. & Spleissen (bis 24F.)": "GF-Kabel vorb. & Spleißen (bis 24F.)",
    "GF-Kabel vorb. & Spleissen (bis 96F.)": "GF-Kabel vorb. & Spleißen (bis 96F.)",
    "Montage und Spleissen von Kopplern":    "Montage und Spleißen von Kopplern",
    "Zusaetzliches Spleissen weiterer Fasern": "Zusätzliches Spleißen weiterer Fasern",
    "GF ungespleisst ablegen":               "GF ungespleißt ablegen",
}

# --- Tabellenraster ----------------------------------------------------------
X_NVT       = (30.5, 68.3)    # Spalte "NVT"
X_TAETIGKEIT = (68.3, 187.1)  # Spalte "Taetigkeit"

# linke/rechte Kante der 9 Mengenspalten, in der Reihenfolge von "col" oben
COLS = [
    (187.1, 250.8),
    (250.8, 308.4),
    (308.4, 381.5),
    (381.5, 436.2),
    (436.2, 494.2),
    (494.2, 554.6),
    (554.6, 611.9),
    (611.9, 660.5),
    (660.5, 717.3),
]

ROW_TOP    = 194.9   # Oberkante Zeile 1
ROW_HEIGHT = 9.483   # Zeilenhoehe
MAX_ROWS   = 30

def row_rect(n, x0, x1):
    """Zellenrechteck (x0, y0, x1, y1) fuer Zeile n (1-basiert)."""
    top = ROW_TOP + (n - 1) * ROW_HEIGHT
    return (x0, top, x1, top + ROW_HEIGHT)

# --- Kopffelder --------------------------------------------------------------
# (x0, x1, y_baseline_unterkante) - Text sitzt knapp ueber der Linie.
# "clear" = True: vorgedruckter Wert wird vorher weiss ueberdeckt.
KOPFFELDER = {
    "ort_datum":        {"box": (111.6, 187.7, 119.2), "clear": True,  "align": "center"},
    "nvt_gebiet":       {"box": (321.8, 382.1, 119.2), "clear": False, "align": "center"},
    "unternehmen":      {"box": (111.6, 187.7, 146.9), "clear": True,  "align": "center"},
    "bv":               {"box": (111.6, 187.7, 155.9), "clear": True,  "align": "center"},
    "projekt":          {"box": (321.8, 382.1, 146.9), "clear": False, "align": "center"},
    "projekt_zusatz":   {"box": (436.7, 494.8, 146.9), "clear": False, "align": "center"},
    "betriebsnetz":     {"box": (321.8, 382.1, 155.9), "clear": False, "align": "center"},
    "betriebsnetz_zusatz": {"box": (494.6, 661.1, 155.9), "clear": False, "align": "center"},
}
