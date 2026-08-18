"""ORM-Roundtrip-Tests: erzeugen, persistieren, wieder lesen."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import NvtStatus, PhotoKind, Ternary
from app.core.models import EnvironmentAnalysis, Nvt, Photo, Project


def _make_project(session: Session) -> Project:
    p = Project(
        name="Testprojekt",
        contractor="Helder Santos GmbH",
        ruleset_version="v1",
        vision_provider="anthropic",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
    )
    session.add(p)
    session.flush()
    return p


def test_project_roundtrip(session: Session) -> None:
    p = _make_project(session)
    session.commit()

    fetched = session.scalars(select(Project).where(Project.id == p.id)).one()
    assert fetched.name == "Testprojekt"
    assert isinstance(fetched.id, UUID)
    assert fetched.ruleset_version == "v1"


def test_nvt_uniqueness_per_project(session: Session) -> None:
    from sqlalchemy.exc import IntegrityError

    p = _make_project(session)
    n1 = Nvt(project_id=p.id, nvt_number="7107", warnings_json=[])
    session.add(n1)
    session.flush()

    n2 = Nvt(project_id=p.id, nvt_number="7107", warnings_json=[])
    session.add(n2)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("Duplikat sollte verhindert werden")


def test_nvt_with_photos_and_env(session: Session) -> None:
    p = _make_project(session)
    nvt = Nvt(project_id=p.id, nvt_number="7107", warnings_json=[])
    session.add(nvt)
    session.flush()

    photo = Photo(
        nvt_id=nvt.id,
        filename="foto1.jpg",
        stored_path="data/projects/x/foto1.jpg",
        mime_type="image/jpeg",
        width=1200,
        height=1600,
        sha256="a" * 64,
        kind=PhotoKind.ORIGINAL,
    )
    session.add(photo)

    env = EnvironmentAnalysis(
        nvt_id=nvt.id,
        road_present=Ternary.YES,
        sidewalk_present=Ternary.YES,
        cycleway_present=Ternary.NO,
        vision_confidence=Decimal("0.9"),
        data_completeness=Decimal("0.8"),
    )
    session.add(env)
    session.commit()

    fetched = session.get(Nvt, nvt.id)
    assert fetched is not None
    assert len(fetched.photos) == 1
    assert fetched.environment is not None
    assert fetched.environment.road_present == Ternary.YES


def test_default_status_is_new(session: Session) -> None:
    p = _make_project(session)
    nvt = Nvt(project_id=p.id, nvt_number="7108", warnings_json=[])
    session.add(nvt)
    session.commit()

    fetched = session.get(Nvt, nvt.id)
    assert fetched is not None
    assert NvtStatus(fetched.status) == NvtStatus.NEW


def test_cascade_delete_removes_children(session: Session) -> None:
    p = _make_project(session)
    nvt = Nvt(project_id=p.id, nvt_number="7107", warnings_json=[])
    session.add(nvt)
    session.flush()
    session.add(
        Photo(
            nvt_id=nvt.id,
            filename="x.jpg",
            stored_path="x",
            mime_type="image/jpeg",
            width=1,
            height=1,
            sha256="b" * 64,
        )
    )
    session.commit()

    session.delete(p)
    session.commit()

    assert session.scalars(select(Nvt)).first() is None
    assert session.scalars(select(Photo)).first() is None
