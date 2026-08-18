"""Tests für den Prompt-Loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.vision.prompts import PromptInvalid, PromptNotFound, load_prompt


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_valid_prompt(tmp_path: Path) -> None:
    _write(
        tmp_path / "greet.md",
        "---\nversion: 2\npurpose: greet\n---\nHallo Welt",
    )
    p = load_prompt("greet", root=tmp_path)
    assert p.name == "greet"
    assert p.version == 2
    assert "Hallo Welt" in p.text
    assert p.frontmatter["purpose"] == "greet"
    assert len(p.sha256) == 64


def test_missing_prompt(tmp_path: Path) -> None:
    with pytest.raises(PromptNotFound):
        load_prompt("nope", root=tmp_path)


def test_no_frontmatter_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "bad.md", "einfach nur Text")
    with pytest.raises(PromptInvalid):
        load_prompt("bad", root=tmp_path)


def test_broken_frontmatter_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "bad.md", "---\nversion: :::\n---\nInhalt")
    with pytest.raises(PromptInvalid):
        load_prompt("bad", root=tmp_path)


def test_real_environment_prompt_is_loadable() -> None:
    """Der eingecheckte prompts/environment_analysis.md muss ladbar sein."""
    from app.config import get_settings

    p = load_prompt("environment_analysis", root=get_settings().prompts_path)
    assert p.version >= 1
    assert "Wähle keinen Regelplan" in p.text
    assert "Zitiere keine Rechtsquellen" in p.text
    assert p.sha256 != ""
