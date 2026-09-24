"""Loader für Referenzfälle unter ``/knowledge/referenzfaelle/``.

Jeder Referenzfall liegt in einem eigenen Ordner ``NVT_71xx/`` mit:

- ``nvt.json`` — Metadaten (Adresse, Regelplan-Label, source_page, notes)
- ``photo.png`` — Optional; per Extraktionsskript erzeugt (nicht ins Git)

Referenzfälle sind **keine Rechtsgrundlage** — sie dokumentieren nur, wie ein
Fall in einer bestehenden freigegebenen VRA behandelt wurde. Das Feld
``kind`` wird bewusst auf ``"reference"`` fixiert.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class ReferenceCaseLoadError(Exception):
    """Wird geworfen, wenn ein Referenzfall-Ordner nicht ladbar ist."""


@dataclass(frozen=True)
class ReferenceCase:
    """Eine dokumentierte Referenz-Zuordnung aus einer bestehenden VRA."""

    nvt_number: str
    source_file: str
    source_page: int | None
    address_street: str | None = None
    address_house_number: str | None = None
    address_postal_code: str | None = None
    address_city: str | None = None
    ruleplan_label: str | None = None
    special_case: str | None = None  # z.B. "Privatfläche", "Betriebsgelände"
    notes: str | None = None
    photo_path: Path | None = None
    lageplan_pages: list[int] = field(default_factory=list)
    extracted_at: datetime | None = None
    kind: str = "reference"

    def has_photo(self) -> bool:
        return self.photo_path is not None and self.photo_path.is_file()

    def is_private_property(self) -> bool:
        marker = (self.special_case or "").lower()
        return any(k in marker for k in ("privat", "betrieb", "stadtnetze", "stadtwerke"))


class ReferenceCaseLibrary:
    """Verzeichnisbasierte Referenzfall-Bibliothek."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._cases: dict[str, ReferenceCase] = {}
        self._loaded = False

    def load(self) -> ReferenceCaseLibrary:
        self._cases.clear()
        if not self.root.exists():
            self._loaded = True
            return self

        for entry_dir in sorted(self.root.iterdir()):
            if not entry_dir.is_dir():
                continue
            metadata_path = entry_dir / "nvt.json"
            if not metadata_path.is_file():
                continue
            case = self._load_one(entry_dir, metadata_path)
            self._cases[case.nvt_number] = case
        self._loaded = True
        return self

    def all(self) -> list[ReferenceCase]:
        if not self._loaded:
            self.load()
        return list(self._cases.values())

    def get(self, nvt_number: str) -> ReferenceCase | None:
        if not self._loaded:
            self.load()
        return self._cases.get(nvt_number)

    def with_ruleplan(self, ruleplan_label: str) -> list[ReferenceCase]:
        return [c for c in self.all() if c.ruleplan_label == ruleplan_label]

    def private_property_cases(self) -> list[ReferenceCase]:
        return [c for c in self.all() if c.is_private_property()]

    def __iter__(self) -> Iterator[ReferenceCase]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self.all())

    # -- Intern --------------------------------------------------------

    def _load_one(self, entry_dir: Path, metadata_path: Path) -> ReferenceCase:
        try:
            data: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReferenceCaseLoadError(
                f"nvt.json in {entry_dir} ist kein valides JSON: {exc}"
            ) from exc

        if "nvt_number" not in data:
            raise ReferenceCaseLoadError(
                f"nvt.json in {entry_dir}: Pflichtfeld 'nvt_number' fehlt"
            )
        if "source_file" not in data:
            raise ReferenceCaseLoadError(
                f"nvt.json in {entry_dir}: Pflichtfeld 'source_file' fehlt"
            )

        # Foto-Pfad relativ zum Ordner
        photo_path: Path | None = None
        candidate = entry_dir / "photo.png"
        if candidate.is_file():
            photo_path = candidate

        extracted_at: datetime | None = None
        if raw_ts := data.get("extracted_at"):
            try:
                extracted_at = datetime.fromisoformat(raw_ts)
            except ValueError:
                extracted_at = None

        return ReferenceCase(
            nvt_number=str(data["nvt_number"]),
            source_file=str(data["source_file"]),
            source_page=data.get("source_page"),
            address_street=data.get("address", {}).get("street"),
            address_house_number=data.get("address", {}).get("house_number"),
            address_postal_code=data.get("address", {}).get("postal_code"),
            address_city=data.get("address", {}).get("city"),
            ruleplan_label=data.get("ruleplan_label"),
            special_case=data.get("special_case"),
            notes=data.get("notes"),
            photo_path=photo_path,
            lageplan_pages=list(data.get("lageplan_pages", [])),
            extracted_at=extracted_at,
            kind=data.get("kind", "reference"),
        )
