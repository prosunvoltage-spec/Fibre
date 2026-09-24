"""Loader für versionierte Markdown-Prompts unter /prompts/.

Jeder Prompt beginnt mit YAML-Frontmatter, der Rest ist der Prompt-Text.
Der SHA-256 der gesamten Datei ist die Version (landet als ``prompt_hash``
in jeder Vision-Antwort — reproduzierbar auditierbar).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import get_settings


class PromptNotFound(FileNotFoundError):
    pass


class PromptInvalid(ValueError):
    pass


@dataclass(frozen=True)
class LoadedPrompt:
    name: str                     # z.B. "environment_analysis"
    version: int                  # aus Frontmatter
    text: str                     # Prompt-Text (ohne Frontmatter)
    frontmatter: dict             # gesamtes Frontmatter für Debug
    sha256: str                   # Hash der Rohdatei
    path: Path


def _parse_frontmatter(raw: str, source: Path) -> tuple[dict, str]:
    """Trennt YAML-Frontmatter vom Prompt-Text.

    Erwartete Form:
        ---
        key: value
        ...
        ---
        (Prompt-Text)
    """
    if not raw.startswith("---"):
        raise PromptInvalid(f"Prompt {source} braucht YAML-Frontmatter (--- am Anfang)")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise PromptInvalid(f"Prompt {source} hat unvollständiges Frontmatter")
    fm_text = parts[1].strip()
    body = parts[2].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise PromptInvalid(f"Prompt {source} hat ungültiges YAML: {exc}") from exc
    if not isinstance(fm, dict):
        raise PromptInvalid(f"Prompt {source} Frontmatter ist kein Mapping")
    return fm, body


def load_prompt(name: str, root: Path | None = None) -> LoadedPrompt:
    root_path = root or get_settings().prompts_path
    file = Path(root_path) / f"{name}.md"
    if not file.is_file():
        raise PromptNotFound(f"Prompt nicht gefunden: {file}")
    raw = file.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    fm, body = _parse_frontmatter(raw.decode("utf-8"), file)
    version = int(fm.get("version", 0))
    return LoadedPrompt(
        name=name,
        version=version,
        text=body.strip(),
        frontmatter=fm,
        sha256=sha,
        path=file,
    )
