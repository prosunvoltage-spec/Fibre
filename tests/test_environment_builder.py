"""End-to-End-Test des EnvironmentBuilder mit MockVision."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from app.classification.environment_builder import EnvironmentBuilder
from app.core.enums import NvtStatus, PhotoKind, Ternary
from app.core.models import Nvt, Photo, Project
from app.core.repositories import ProjectRepo
from app.core.schemas import ProjectCreate
from app.vision import MockVisionProvider, VisionPipeline
from app.vision.prompts import LoadedPrompt


@pytest.fixture()
def prompt() -> LoadedPrompt:
    return LoadedPrompt(
        name="test",
        version=1,
        text="…",
        frontmatter={"version": 1},
        sha256="b" * 64,
        path=Path("/tmp/test.md"),
    )


def _jpg(path: Path, color: str = "gray") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=color).save(path, "JPEG")


def _make_project_and_nvt(session: Session, tmp_path: Path, filename: str) -> Nvt:
    project = ProjectRepo(session).create(
        ProjectCreate(
            name="P",
            contractor="F",
            ruleset_version="v1",
            vision_provider="mock",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
        )
    )
    photo_path = tmp_path / filename
    _jpg(photo_path)
    nvt = Nvt(project_id=project.id, nvt_number="7107", warnings_json=[])
    session.add(nvt)
    session.flush()
    photo = Photo(
        nvt_id=nvt.id,
        filename=filename,
        stored_path=str(photo_path),
        mime_type="image/jpeg",
        width=16,
        height=16,
        sha256="c" * 64,
        kind=PhotoKind.ORIGINAL,
    )
    session.add(photo)
    session.flush()
    return nvt


def test_builder_success_creates_environment(session: Session, tmp_path: Path, prompt: LoadedPrompt) -> None:
    nvt = _make_project_and_nvt(session, tmp_path, "front.jpg")
    provider = MockVisionProvider(
        responses={
            "front.jpg": {
                "road_present": "yes",
                "sidewalk_present": "yes",
                "cycleway_present": "no",
                "nvt_position": "at_roadside",
                "road_class": "hauptverkehr",
                "vision_confidence": 0.9,
                "manual_review_suggested": False,
            }
        }
    )
    builder = EnvironmentBuilder(session, VisionPipeline(provider, prompt), user="tester")
    outcome = builder.analyze(nvt)

    assert outcome.environment_created is True
    assert NvtStatus(nvt.status) == NvtStatus.ANALYZED
    assert nvt.environment is not None
    assert nvt.environment.road_present == Ternary.YES
    assert nvt.environment.prompt_hash == prompt.sha256


def test_builder_unknown_response_forces_review(session: Session, tmp_path: Path, prompt: LoadedPrompt) -> None:
    nvt = _make_project_and_nvt(session, tmp_path, "unknown.jpg")
    builder = EnvironmentBuilder(session, VisionPipeline(MockVisionProvider(), prompt))
    outcome = builder.analyze(nvt)

    assert outcome.environment_created is True
    assert outcome.manual_review_required is True
    assert NvtStatus(nvt.status) == NvtStatus.NEEDS_REVIEW


def test_builder_fails_gracefully_without_photos(session: Session, tmp_path: Path, prompt: LoadedPrompt) -> None:
    project = ProjectRepo(session).create(
        ProjectCreate(
            name="P",
            contractor="F",
            ruleset_version="v1",
            vision_provider="mock",
        )
    )
    nvt = Nvt(project_id=project.id, nvt_number="7107", warnings_json=[])
    session.add(nvt)
    session.flush()

    builder = EnvironmentBuilder(session, VisionPipeline(MockVisionProvider(), prompt))
    outcome = builder.analyze(nvt)
    assert outcome.environment_created is False
    assert outcome.manual_review_required is True


def test_second_analyze_needs_force(session: Session, tmp_path: Path, prompt: LoadedPrompt) -> None:
    nvt = _make_project_and_nvt(session, tmp_path, "a.jpg")
    provider = MockVisionProvider(responses={"a.jpg": {"road_present": "yes", "vision_confidence": 0.9}})
    builder = EnvironmentBuilder(session, VisionPipeline(provider, prompt))
    builder.analyze(nvt)

    # zweiter Aufruf ohne force → skip
    outcome = builder.analyze(nvt)
    assert outcome.environment_created is False
    assert "existiert bereits" in outcome.warnings[0]

    outcome = builder.analyze(nvt, force=True)
    assert outcome.environment_created is True
