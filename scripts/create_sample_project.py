"""Legt ein Beispiel-Projekt mit ein paar NVTs an.

Braucht eine initialisierte DB (``make migrate``). Ist idempotent — wenn das
Projekt schon existiert, wird nichts erzeugt.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Erlaubt Aufruf via `python scripts/create_sample_project.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import get_settings
from app.core.db import session_scope
from app.core.models import Project
from app.core.repositories import NvtRepo, ProjectRepo
from app.core.schemas import AddressSchema, LocationSchema, NvtCreate, ProjectCreate

SAMPLE_NAME = "Roxel Einblasarbeiten – Beispiel"

# Auszug aus docs/REFERENCE_CASES.md; nur zum Vorführen der DB-Struktur.
SAMPLE_NVTS: list[dict[str, str]] = [
    {"number": "7107", "street": "Roxeler Straße", "house_number": "579", "city": "Münster"},
    {"number": "7116", "street": "Lindenstraße", "house_number": "2A", "city": "Münster"},
    {"number": "7124", "street": "Stellmacherweg", "house_number": "31", "city": "Münster"},
]


def main() -> int:
    settings = get_settings()
    print(f"→ DB: {settings.database_url}")

    with session_scope() as session:
        projects = ProjectRepo(session)
        nvts = NvtRepo(session)

        existing = session.scalars(select(Project).where(Project.name == SAMPLE_NAME)).first()
        if existing is not None:
            print(f"  Projekt '{SAMPLE_NAME}' existiert bereits (id={existing.id}).")
            return 0

        project = projects.create(
            ProjectCreate(
                name=SAMPLE_NAME,
                location_label="Münster-Roxel",
                period_start=date(2026, 7, 3),
                period_end=date(2026, 8, 15),
                client="Stadtnetze Münster",
                contractor="Helder Santos GmbH & Co. KG",
                site_manager_name="dos Santos, Kelly",
                on_site_responsible_name="Nessen, Nico",
                on_site_responsible_phone="0155 – 62 55 30 86",
                ruleset_version=settings.current_ruleset_version,
                vision_provider=settings.vision_provider,
            )
        )
        print(f"✓ Projekt '{project.name}' angelegt (id={project.id})")

        for entry in SAMPLE_NVTS:
            nvt = nvts.create(
                NvtCreate(
                    project_id=project.id,
                    nvt_number=entry["number"],
                    address=AddressSchema(
                        street=entry["street"],
                        house_number=entry["house_number"],
                        city=entry["city"],
                        postal_code="48161",
                    ),
                    location=LocationSchema(),
                )
            )
            print(f"  + NVT {nvt.nvt_number} ({entry['street']} {entry['house_number']})")

    print("Fertig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
