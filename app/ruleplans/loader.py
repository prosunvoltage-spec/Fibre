"""Loader für die Regelplan-Bibliothek unter ``/knowledge/regelplaene/``.

Jeder Regelplan liegt in einem eigenen Unterordner. Erwartete Dateien:

- ``metadata.json``  — Pflicht, wird gegen :class:`RulePlanSchema` validiert
- ``plan.pdf``       — Optional (bei bereitgestellter Regelplan-Zeichnung)
- ``preview.png``    — Optional (Vorschau für die UI)

Halluzinations-Schutz:

- Der Loader **erfindet keine Werte**. Fehlt ein Pflichtfeld, wird
  ``is_complete=False`` gesetzt und eine :class:`RulePlanValidationIssue`
  gesammelt.
- ``revision_hash`` wird als SHA-256 der Rohdatei berechnet — Änderungen an
  ``metadata.json`` sind damit versionierbar.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from app.core.schemas import RulePlanSchema


class RulePlanLoadError(Exception):
    """Wird geworfen, wenn ein Regelplan-Ordner nicht ladbar ist."""


@dataclass(frozen=True)
class RulePlanValidationIssue:
    """Fachliche Unvollständigkeit eines Regelplans."""

    ruleplan_id: str
    field: str
    message: str


@dataclass
class RulePlanEntry:
    """Ein geladener Regelplan mit optionalen Warnungen."""

    schema: RulePlanSchema
    issues: list[RulePlanValidationIssue] = field(default_factory=list)


class RulePlanLibrary:
    """Verzeichnisbasierte Regelplan-Bibliothek."""

    _REQUIRED_FIELDS_FOR_COMPLETENESS: tuple[str, ...] = (
        "verkehrsraum",
        "geeignet_fuer",
        "voraussetzungen",
        "allowed_symbols",
    )

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._entries: dict[str, RulePlanEntry] = {}
        self._loaded = False

    # -- Öffentliche API -----------------------------------------------

    def load(self) -> RulePlanLibrary:
        """(Erneut) einlesen. Idempotent."""
        self._entries.clear()
        if not self.root.exists():
            self._loaded = True
            return self

        for entry_dir in sorted(self.root.iterdir()):
            if not entry_dir.is_dir():
                continue
            metadata_path = entry_dir / "metadata.json"
            if not metadata_path.is_file():
                continue
            entry = self._load_one(entry_dir, metadata_path)
            self._entries[entry.schema.id] = entry
        self._loaded = True
        return self

    def all(self) -> list[RulePlanEntry]:
        if not self._loaded:
            self.load()
        return list(self._entries.values())

    def ids(self) -> list[str]:
        return [e.schema.id for e in self.all()]

    def get(self, ruleplan_id: str) -> RulePlanEntry | None:
        if not self._loaded:
            self.load()
        return self._entries.get(ruleplan_id)

    def __iter__(self) -> Iterator[RulePlanEntry]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self.all())

    def complete_ids(self) -> list[str]:
        return [e.schema.id for e in self.all() if e.schema.is_complete]

    def incomplete_ids(self) -> list[str]:
        return [e.schema.id for e in self.all() if not e.schema.is_complete]

    def all_issues(self) -> list[RulePlanValidationIssue]:
        return [i for e in self.all() for i in e.issues]

    # -- Intern --------------------------------------------------------

    def _load_one(self, entry_dir: Path, metadata_path: Path) -> RulePlanEntry:
        raw = metadata_path.read_bytes()
        revision_hash = hashlib.sha256(raw).hexdigest()

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RulePlanLoadError(
                f"metadata.json in {entry_dir} ist kein valides JSON: {exc}"
            ) from exc

        # Interne Hilfsfelder (mit "_"-Präfix) sind KEIN Teil des Schemas
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        # Pfade auf die Binaries werden immer relativ zur Bibliothek gesetzt
        data.setdefault("plan_pdf_path", str(entry_dir / "plan.pdf"))
        data.setdefault("preview_png_path", str(entry_dir / "preview.png"))
        data["revision_hash"] = revision_hash

        # is_complete aus Feld-Vollständigkeit ableiten, nicht vom JSON glauben
        computed_complete, issues = self._compute_completeness(data, entry_dir.name)
        data["is_complete"] = computed_complete

        try:
            schema = RulePlanSchema(**data)
        except ValidationError as exc:
            raise RulePlanLoadError(
                f"metadata.json in {entry_dir} verletzt Schema: {exc}"
            ) from exc

        return RulePlanEntry(schema=schema, issues=issues)

    def _compute_completeness(
        self, data: dict, dir_name: str
    ) -> tuple[bool, list[RulePlanValidationIssue]]:
        issues: list[RulePlanValidationIssue] = []
        ruleplan_id = data.get("id") or dir_name

        for field_name in self._REQUIRED_FIELDS_FOR_COMPLETENESS:
            value = data.get(field_name)
            if not value:
                issues.append(
                    RulePlanValidationIssue(
                        ruleplan_id=ruleplan_id,
                        field=field_name,
                        message=(
                            f"'{field_name}' ist leer — Regelplan wird nicht "
                            "automatisch vorgeschlagen"
                        ),
                    )
                )

        for req_field in ("voraussetzungen", "ausschlusskriterien"):
            for i, req in enumerate(data.get(req_field, []) or []):
                if not isinstance(req, dict):
                    continue
                if not req.get("source_document"):
                    issues.append(
                        RulePlanValidationIssue(
                            ruleplan_id=ruleplan_id,
                            field=f"{req_field}[{i}].source_document",
                            message="Quellenangabe fehlt (Halluzinations-Schutz)",
                        )
                    )

        # Binaries prüfen (optional, aber Warnung wenn nicht da)
        for path_field in ("plan_pdf_path", "preview_png_path"):
            p = Path(data.get(path_field, ""))
            if not p.is_file():
                issues.append(
                    RulePlanValidationIssue(
                        ruleplan_id=ruleplan_id,
                        field=path_field,
                        message=f"Datei fehlt: {p}",
                    )
                )

        return (len(issues) == 0), issues
