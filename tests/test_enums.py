"""Tests für Enum-Werte und Statuswechsel-Tabelle."""

from __future__ import annotations

import pytest

from app.core.enums import (
    NVT_STATUS_TRANSITIONS,
    NvtStatus,
    is_valid_transition,
)


def test_all_statuses_in_transition_table() -> None:
    """Jeder NvtStatus taucht als Schlüssel in der Übergangstabelle auf."""
    for status in NvtStatus:
        assert status in NVT_STATUS_TRANSITIONS


def test_new_can_go_to_analyzing() -> None:
    assert is_valid_transition(NvtStatus.NEW, NvtStatus.ANALYZING)


def test_exported_is_terminal() -> None:
    for target in NvtStatus:
        assert not is_valid_transition(NvtStatus.EXPORTED, target)


def test_approved_can_be_exported_or_reopened() -> None:
    assert is_valid_transition(NvtStatus.APPROVED, NvtStatus.EXPORTED)
    assert is_valid_transition(NvtStatus.APPROVED, NvtStatus.NEEDS_REVIEW)
    # aber nicht direkt zurück auf ANALYZING
    assert not is_valid_transition(NvtStatus.APPROVED, NvtStatus.ANALYZING)


def test_new_cannot_jump_to_approved() -> None:
    assert not is_valid_transition(NvtStatus.NEW, NvtStatus.APPROVED)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (NvtStatus.NEEDS_REVIEW, NvtStatus.REVIEWED),
        (NvtStatus.REVIEWED, NvtStatus.APPROVED),
        (NvtStatus.REJECTED, NvtStatus.NEEDS_REVIEW),
    ],
)
def test_valid_paths(current: NvtStatus, target: NvtStatus) -> None:
    assert is_valid_transition(current, target)
