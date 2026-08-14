"""Legt die initialen Metadaten-JSONs für Referenzfälle + Regelpläne an.

Die Daten stammen aus ``docs/REFERENCE_CASES.md`` und wurden dort handkuratiert
aus der Roxel-VRA (Stadt Münster, 02.07.2026). Sie werden hier in einzelne
``nvt.json`` bzw. ``metadata.json`` überführt.

Idempotent: Bereits existierende Dateien werden NICHT überschrieben (außer
mit ``--force``). Damit können Fachanwender pflegen, ohne dass ein späterer
Skript-Lauf ihre Änderungen zerstört.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Aufruf per `python scripts/bootstrap_knowledge.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings

SOURCE_FILE = "Roxel_alle_NVT_Einblasarbeiten_weiterer_Durchfuehrungszeitraum_02072026.pdf"

# ----------------------------------------------------------------------------
# Referenzfälle (25 NVT) — Quelle: docs/REFERENCE_CASES.md, handkuratiert aus
# den Kamera-Overlays der Foto-Seiten und aus den Lageplan-Beschriftungen der
# Referenz-PDF. Adressen sind NICHT geokodiert; PLZ wo im Overlay lesbar.
# ----------------------------------------------------------------------------

REFERENCE_CASES: list[dict] = [
    {
        "nvt_number": "7101",
        "source_page": 3,
        "address": {"street": "Havixbecker Straße", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B2/2",
        "notes": "Straße mit Radweg, Ortsrand",
    },
    {
        "nvt_number": "7102",
        "source_page": 3,
        "address": {"street": "Buschkamp", "house_number": "8A", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "s. Foto",
        "notes": "Grundstückszufahrt / Wohnstraße; Regelplan auf Foto eingezeichnet",
    },
    {
        "nvt_number": "7103",
        "source_page": 5,
        "address": {"street": "Auf dem Dorn", "house_number": "10", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B1/15",
        "notes": "Sackgasse — Vollsperrung, Gehweg über Straße",
    },
    {
        "nvt_number": "7104",
        "source_page": 6,
        "address": {"street": "Brockkamp", "house_number": "76", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B1/2",
        "notes": "Sackgassen-Ende, NVT an Zufahrt",
        "lageplan_pages": [8],
    },
    {
        "nvt_number": "7105",
        "source_page": 9,
        "address": {"street": "Brockkamp", "house_number": "16", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "special_case": "nur innerhalb Stadtnetze-Gelände",
        "notes": "7105 + 7106 kombiniert; Betriebsgelände",
        "lageplan_pages": [10],
    },
    {
        "nvt_number": "7106",
        "source_page": 9,
        "address": {"street": "Brockkamp", "house_number": "16", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "special_case": "nur innerhalb Stadtnetze-Gelände",
        "notes": "siehe 7105",
        "lageplan_pages": [10],
    },
    {
        "nvt_number": "7107",
        "source_page": 11,
        "address": {"street": "Roxeler Straße", "house_number": "579", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B2/2",
        "notes": "Hauptverkehrsstraße, NVT am Fahrbahnrand",
        "lageplan_pages": [12, 13],
    },
    {
        "nvt_number": "7108",
        "source_page": 14,
        "address": {"street": "Schulze-Hermann-Straße", "house_number": "7", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B2/2",
        "notes": "Streetview-Zusatzfoto zur Fußgängerführung über K&K-Ladefläche",
        "lageplan_pages": [15, 16],
    },
    {
        "nvt_number": "7109",
        "source_page": 17,
        "address": {"street": "Große Helkamp", "house_number": "19B", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "special_case": "Privatfläche",
        "notes": "keine öffentliche VRA nötig",
        "lageplan_pages": [18],
    },
    {
        "nvt_number": "7110",
        "source_page": 19,
        "address": {"city": "Münster"},
        "ruleplan_label": "B1/2",
        "notes": "NVT in Grundstückszufahrt/Wohnstraße; Straßenname im Overlay nicht lesbar",
        "lageplan_pages": [20],
    },
    {
        "nvt_number": "7111",
        "source_page": 21,
        "address": {"street": "Schutte-Bern-Straße", "house_number": "28", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Aufnahme im Grünbereich",
        "lageplan_pages": [22],
    },
    {
        "nvt_number": "7112",
        "source_page": 23,
        "address": {"street": "Carossastraße", "house_number": "46", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Gehwegseite",
        "lageplan_pages": [24],
    },
    {
        "nvt_number": "7113",
        "source_page": 25,
        "address": {"street": "Ricarda-Huch-Straße", "house_number": "31A", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "special_case": "Privatgelände der Stadtnetze Münster",
        "notes": "keine öffentliche VRA",
        "lageplan_pages": [26],
    },
    {
        "nvt_number": "7114",
        "source_page": 27,
        "address": {"street": "Kösters Kämpken", "house_number": "36a", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "special_case": "Privatgelände der Stadtnetze",
        "notes": "keine öffentliche VRA",
        "lageplan_pages": [28],
    },
    {
        "nvt_number": "7115",
        "source_page": 29,
        "address": {"street": "Goldaper Straße", "house_number": "4", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B1/2",
        "notes": "Wohnstraße, NVT im Seitenbereich",
        "lageplan_pages": [30],
    },
    {
        "nvt_number": "7116",
        "source_page": 31,
        "address": {"street": "Lindenstraße", "house_number": "2A", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Gehweg-Situation",
        "lageplan_pages": [32],
    },
    {
        "nvt_number": "7117",
        "source_page": 33,
        "address": {"street": "Buchenweg", "house_number": "22", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Wohnstraße, Firmenwasserzeichen im Foto",
        "lageplan_pages": [34],
    },
    {
        "nvt_number": "7118",
        "source_page": 35,
        "address": {"street": "Schelmenstiege", "house_number": "34-38", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Wohnstraße-Kurve",
        "lageplan_pages": [36],
    },
    {
        "nvt_number": "7119",
        "source_page": 37,
        "address": {"street": "Am Rohrbusch", "house_number": "22", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B2/2",
        "notes": "Radwegsituation, größere Straße",
        "lageplan_pages": [38],
    },
    {
        "nvt_number": "7120",
        "source_page": 39,
        "address": {"street": "Alte Landstraße", "house_number": "10", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B1/2",
        "notes": "Zufahrt/Gewerbegebiet",
        "lageplan_pages": [40],
    },
    {
        "nvt_number": "7121",
        "source_page": None,
        "address": {"street": "Bertolt-Brecht-Straße", "house_number": "26", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "notes": "In dieser PDF nur Lageplan, kein Fotoblatt; anhand Referenzunterlagen prüfen",
        "lageplan_pages": [41],
    },
    {
        "nvt_number": "7122",
        "source_page": None,
        "address": {"street": "Ludwig-Thoma-Straße", "house_number": "104", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": None,
        "notes": "In dieser PDF nur Lageplan; anhand Referenzunterlagen prüfen",
        "lageplan_pages": [42],
    },
    {
        "nvt_number": "7123",
        "source_page": 43,
        "address": {"street": "Schildstiege", "house_number": "4", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Wohnstraße",
        "lageplan_pages": [44, 45],
    },
    {
        "nvt_number": "7124",
        "source_page": 46,
        "address": {"street": "Stellmacherweg", "house_number": "31", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "B1/2",
        "notes": "Wohnstraße-Kurve",
        "lageplan_pages": [47, 48],
    },
    {
        "nvt_number": "7125",
        "source_page": 49,
        "address": {"street": "Korbmacherweg", "house_number": "14A", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "zusätzlicher Streetview-Ausschnitt",
        "lageplan_pages": [50],
    },
    {
        "nvt_number": "7126",
        "source_page": 51,
        "address": {"street": "Stellmacherweg", "house_number": "212A", "postal_code": "48161", "city": "Münster"},
        "ruleplan_label": "VZP1",
        "notes": "Wohnstraßen-Kurve",
        "lageplan_pages": [52],
    },
]

# ----------------------------------------------------------------------------
# Regelpläne (4) — Quelle: Roxel-VRA S. 53–56. Fachliche Felder BLEIBEN LEER
# und müssen vom Fachanwender aus RSA 21 nachgetragen werden.
# ----------------------------------------------------------------------------

RULEPLANS: list[dict] = [
    {
        "dir": "VZP1",
        "id": "VZP1",
        "name": "Verkehrszeichenplan 1 – Stadt Münster",
        "quelle": "Stadt Münster / Referenz-VRA Roxel",
        "version": "2026",
        "beschreibung": "Kurzzeitige punktuelle Absicherung im Wohnstraßen-/Seitenbereich",
        "source_page": 53,
    },
    {
        "dir": "B1_2",
        "id": "B1/2",
        "name": "Regelplan B I/2 modifiziert",
        "quelle": "RSA 21 Teil D",
        "version": "08.21",
        "beschreibung": "Straße mit geringer Verkehrsstärke oder in geschwindigkeitsreduziertem Bereich mit deutlicher Einengung",
        "source_page": 54,
    },
    {
        "dir": "B2_2",
        "id": "B2/2",
        "name": "Regelplan B II/2",
        "quelle": "RSA 21 Teil D",
        "version": "08.21",
        "beschreibung": "Paralleler Geh- und Radweg mit Sperrung des Radweges; geringe Einengung der Fahrbahn",
        "source_page": 55,
    },
    {
        "dir": "B1_15",
        "id": "B1/15",
        "name": "Regelplan B I/15",
        "quelle": "RSA 21 Teil D",
        "version": "05.21",
        "beschreibung": "Sperrung einer Straße",
        "source_page": 56,
    },
]


def _empty_metadata_shell(rp: dict) -> dict:
    """Regelplan-Metadaten mit leeren Pflichtfeldern (Fachanwender füllt)."""
    return {
        "id": rp["id"],
        "name": rp["name"],
        "quelle": rp["quelle"],
        "version": rp["version"],
        "beschreibung": rp["beschreibung"],
        "source_file": SOURCE_FILE,
        "source_page": rp["source_page"],
        "verkehrsraum": [],
        "geeignet_fuer": [],
        "voraussetzungen": [],
        "ausschlusskriterien": [],
        "fussverkehr": {},
        "radverkehr": {},
        "fahrverkehr": {},
        "besondere_hinweise": [],
        "allowed_symbols": [],
        "_todo": (
            "Fachanwender: Pflichtfelder aus RSA 21 nachtragen "
            "(verkehrsraum, geeignet_fuer, voraussetzungen, allowed_symbols). "
            "Bis dahin bleibt is_complete=false und dieser Regelplan wird "
            "niemals AUTO_VORSCHLAG."
        ),
    }


def _reference_case_shell(rc: dict) -> dict:
    address = rc.get("address") or {}
    return {
        "nvt_number": rc["nvt_number"],
        "source_file": SOURCE_FILE,
        "source_page": rc.get("source_page"),
        "address": {
            "street": address.get("street"),
            "house_number": address.get("house_number"),
            "postal_code": address.get("postal_code"),
            "city": address.get("city"),
            "country": "DE",
        },
        "ruleplan_label": rc.get("ruleplan_label"),
        "special_case": rc.get("special_case"),
        "notes": rc.get("notes"),
        "lageplan_pages": rc.get("lageplan_pages", []),
        "extracted_at": None,
        "kind": "reference",
    }


def _write_json(path: Path, data: dict, force: bool) -> str:
    if path.exists() and not force:
        return "skip"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return "write"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Bestehende Dateien überschreiben."
    )
    args = parser.parse_args()

    settings = get_settings()
    knowledge = settings.knowledge_path
    ref_dir = knowledge / "referenzfaelle"
    rp_dir = knowledge / "regelplaene"

    counts = {"reference_cases": {"write": 0, "skip": 0}, "ruleplans": {"write": 0, "skip": 0}}

    for rc in REFERENCE_CASES:
        target = ref_dir / f"NVT_{rc['nvt_number']}" / "nvt.json"
        action = _write_json(target, _reference_case_shell(rc), args.force)
        counts["reference_cases"][action] += 1
        print(f"  [{action}] {target.relative_to(knowledge.parent)}")

    for rp in RULEPLANS:
        target = rp_dir / rp["dir"] / "metadata.json"
        action = _write_json(target, _empty_metadata_shell(rp), args.force)
        counts["ruleplans"][action] += 1
        print(f"  [{action}] {target.relative_to(knowledge.parent)}")

    print()
    print(
        f"Referenzfälle: {counts['reference_cases']['write']} geschrieben, "
        f"{counts['reference_cases']['skip']} übersprungen"
    )
    print(
        f"Regelpläne:    {counts['ruleplans']['write']} geschrieben, "
        f"{counts['ruleplans']['skip']} übersprungen"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
