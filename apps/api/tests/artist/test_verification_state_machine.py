"""Pure unit tests for the transition tables in app/db/enums.py — no DB
needed. API-level enforcement of these rules is covered separately in
tests/artist/test_onboarding.py and test_admin_verification.py."""

import pytest

from app.db.enums import (
    ArtistVerificationStatus as S,
)
from app.db.enums import (
    is_valid_artist_self_transition,
    is_valid_artist_staff_transition,
)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.DRAFT.value, S.SUBMITTED.value),
        (S.REJECTED.value, S.SUBMITTED.value),
        (S.MORE_INFORMATION_REQUIRED.value, S.SUBMITTED.value),
    ],
)
def test_valid_self_transitions(from_status: str, to_status: str) -> None:
    assert is_valid_artist_self_transition(from_status, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.SUBMITTED.value, S.SUBMITTED.value),
        (S.UNDER_REVIEW.value, S.SUBMITTED.value),
        (S.APPROVED.value, S.SUBMITTED.value),
        (S.SUSPENDED.value, S.SUBMITTED.value),
        (S.DRAFT.value, S.APPROVED.value),
    ],
)
def test_invalid_self_transitions(from_status: str, to_status: str) -> None:
    assert not is_valid_artist_self_transition(from_status, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.SUBMITTED.value, S.UNDER_REVIEW.value),
        (S.UNDER_REVIEW.value, S.APPROVED.value),
        (S.UNDER_REVIEW.value, S.REJECTED.value),
        (S.UNDER_REVIEW.value, S.MORE_INFORMATION_REQUIRED.value),
        (S.APPROVED.value, S.SUSPENDED.value),
        (S.SUSPENDED.value, S.APPROVED.value),
    ],
)
def test_valid_staff_transitions(from_status: str, to_status: str) -> None:
    assert is_valid_artist_staff_transition(from_status, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.DRAFT.value, S.UNDER_REVIEW.value),
        (S.SUBMITTED.value, S.APPROVED.value),
        (S.REJECTED.value, S.APPROVED.value),
        (S.MORE_INFORMATION_REQUIRED.value, S.APPROVED.value),
        (S.SUSPENDED.value, S.REJECTED.value),
    ],
)
def test_invalid_staff_transitions(from_status: str, to_status: str) -> None:
    assert not is_valid_artist_staff_transition(from_status, to_status)
