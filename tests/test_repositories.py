"""Tests für die CRUD-Repositories + State-Machine-Guard."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.enums import NvtStatus, ReviewAction
from app.core.repositories import (
    AuditRepo,
    DuplicateNvtNumberError,
    InvalidStateTransition,
    NvtRepo,
    ProjectRepo,
)
from app.core.schemas import (
    AddressSchema,
    LocationSchema,
    NvtCreate,
    ProjectCreate,
)


@pytest.fixture()
def project(session: Session):
    repo = ProjectRepo(session)
    return repo.create(
        ProjectCreate(
            name="Roxel Einblasarbeiten 2026",
            contractor="Helder Santos GmbH & Co. KG",
            ruleset_version="v1",
            vision_provider="anthropic",
        )
    )


def test_project_crud(session: Session) -> None:
    repo = ProjectRepo(session)
    created = repo.create(
        ProjectCreate(
            name="X",
            contractor="Y",
            ruleset_version="v1",
            vision_provider="anthropic",
        )
    )
    assert repo.get(created.id) is not None
    assert len(repo.list()) == 1

    assert repo.delete(created.id) is True
    assert repo.get(created.id) is None


def test_nvt_create_and_find(session: Session, project) -> None:
    repo = NvtRepo(session)
    nvt = repo.create(
        NvtCreate(
            project_id=project.id,
            nvt_number="7107",
            address=AddressSchema(street="Roxeler Straße", house_number="579"),
            location=LocationSchema(),
        )
    )
    assert nvt.address_json == {
        "street": "Roxeler Straße",
        "house_number": "579",
        "postal_code": None,
        "city": None,
        "country": "DE",
        "raw": None,
        "source": None,
    }
    found = repo.find_by_number(project.id, "7107")
    assert found is not None and found.id == nvt.id


def test_nvt_duplicate_raises(session: Session, project) -> None:
    repo = NvtRepo(session)
    repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))
    with pytest.raises(DuplicateNvtNumberError):
        repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))


def test_nvt_valid_state_flow(session: Session, project) -> None:
    repo = NvtRepo(session)
    nvt = repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))
    assert NvtStatus(nvt.status) == NvtStatus.NEW

    repo.update_status(nvt, NvtStatus.ANALYZING)
    repo.update_status(nvt, NvtStatus.ANALYZED)
    repo.update_status(nvt, NvtStatus.NEEDS_REVIEW)
    repo.update_status(nvt, NvtStatus.REVIEWED)
    repo.update_status(nvt, NvtStatus.APPROVED)
    repo.update_status(nvt, NvtStatus.EXPORTED)

    assert NvtStatus(nvt.status) == NvtStatus.EXPORTED


def test_nvt_invalid_state_transition(session: Session, project) -> None:
    repo = NvtRepo(session)
    nvt = repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))
    with pytest.raises(InvalidStateTransition) as exc:
        repo.update_status(nvt, NvtStatus.APPROVED)
    assert exc.value.current == NvtStatus.NEW
    assert exc.value.target == NvtStatus.APPROVED


def test_exported_is_terminal(session: Session, project) -> None:
    repo = NvtRepo(session)
    nvt = repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))
    # kürzester Weg nach EXPORTED
    for target in [
        NvtStatus.ANALYZING,
        NvtStatus.ANALYZED,
        NvtStatus.NEEDS_REVIEW,
        NvtStatus.REVIEWED,
        NvtStatus.APPROVED,
        NvtStatus.EXPORTED,
    ]:
        repo.update_status(nvt, target)

    with pytest.raises(InvalidStateTransition):
        repo.update_status(nvt, NvtStatus.NEEDS_REVIEW)


def test_add_warning_is_idempotent(session: Session, project) -> None:
    repo = NvtRepo(session)
    nvt = repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))
    repo.add_warning(nvt, "Bild überbelichtet")
    repo.add_warning(nvt, "Bild überbelichtet")
    repo.add_warning(nvt, "GPS unklar")
    assert nvt.warnings_json == ["Bild überbelichtet", "GPS unklar"]


def test_audit_append_and_list(session: Session, project) -> None:
    nvt_repo = NvtRepo(session)
    audit = AuditRepo(session)
    nvt = nvt_repo.create(NvtCreate(project_id=project.id, nvt_number="7107"))

    audit.append(
        action=ReviewAction.RULEPLAN_CHANGED.value,
        user="nico.n",
        project_id=project.id,
        nvt_id=nvt.id,
        old_value="B1/2",
        new_value="B2/2",
        payload={"comment": "Verkehrsstärke höher"},
    )
    audit.append(
        action=ReviewAction.APPROVED.value,
        user="nico.n",
        project_id=project.id,
        nvt_id=nvt.id,
    )

    entries = audit.list_for_nvt(nvt.id)
    assert len(entries) == 2
    # neueste zuerst
    assert entries[0].action == ReviewAction.APPROVED.value
    assert entries[1].old_value == "B1/2"
