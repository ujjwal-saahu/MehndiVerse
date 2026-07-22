"""Pure validation of the booking status state machine — no database needed.
See docs/booking-lifecycle.md."""

import pytest

from app.db.enums import (
    BOOKING_STATUS_TRANSITIONS,
    TERMINAL_BOOKING_STATUSES,
    BookingStatus,
    is_valid_booking_transition,
)


def test_initial_transition_is_draft_only() -> None:
    assert is_valid_booking_transition(None, BookingStatus.DRAFT)
    assert not is_valid_booking_transition(None, BookingStatus.REQUESTED)
    assert not is_valid_booking_transition(None, BookingStatus.CONFIRMED)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (BookingStatus.DRAFT, BookingStatus.REQUESTED),
        (BookingStatus.DRAFT, BookingStatus.CANCELLED),
        (BookingStatus.REQUESTED, BookingStatus.ARTIST_REVIEWING),
        (BookingStatus.REQUESTED, BookingStatus.QUOTATION_SENT),
        (BookingStatus.REQUESTED, BookingStatus.REJECTED),
        (BookingStatus.REQUESTED, BookingStatus.CANCELLED),
        (BookingStatus.ARTIST_REVIEWING, BookingStatus.QUOTATION_SENT),
        (BookingStatus.ARTIST_REVIEWING, BookingStatus.REJECTED),
        (BookingStatus.ARTIST_REVIEWING, BookingStatus.CANCELLED),
        (BookingStatus.QUOTATION_SENT, BookingStatus.CUSTOMER_REVIEWING),
        (BookingStatus.QUOTATION_SENT, BookingStatus.CONFIRMED),
        (BookingStatus.QUOTATION_SENT, BookingStatus.DEPOSIT_PENDING),
        (BookingStatus.QUOTATION_SENT, BookingStatus.REJECTED),
        (BookingStatus.QUOTATION_SENT, BookingStatus.CANCELLED),
        (BookingStatus.CUSTOMER_REVIEWING, BookingStatus.CONFIRMED),
        (BookingStatus.CUSTOMER_REVIEWING, BookingStatus.DEPOSIT_PENDING),
        (BookingStatus.CUSTOMER_REVIEWING, BookingStatus.REJECTED),
        (BookingStatus.CUSTOMER_REVIEWING, BookingStatus.CANCELLED),
        (BookingStatus.CONFIRMED, BookingStatus.DEPOSIT_PENDING),
        (BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS),
        (BookingStatus.CONFIRMED, BookingStatus.CANCELLED),
        (BookingStatus.CONFIRMED, BookingStatus.DISPUTED),
        (BookingStatus.DEPOSIT_PENDING, BookingStatus.DEPOSIT_PAID),
        (BookingStatus.DEPOSIT_PENDING, BookingStatus.CANCELLED),
        (BookingStatus.DEPOSIT_PENDING, BookingStatus.DISPUTED),
        (BookingStatus.DEPOSIT_PAID, BookingStatus.IN_PROGRESS),
        (BookingStatus.DEPOSIT_PAID, BookingStatus.CANCELLED),
        (BookingStatus.DEPOSIT_PAID, BookingStatus.DISPUTED),
        (BookingStatus.IN_PROGRESS, BookingStatus.COMPLETED),
        (BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED),
        (BookingStatus.IN_PROGRESS, BookingStatus.DISPUTED),
        (BookingStatus.COMPLETED, BookingStatus.REFUND_REQUESTED),
        (BookingStatus.REFUND_REQUESTED, BookingStatus.REFUNDED),
        (BookingStatus.REFUND_REQUESTED, BookingStatus.COMPLETED),
        (BookingStatus.DISPUTED, BookingStatus.COMPLETED),
        (BookingStatus.DISPUTED, BookingStatus.CANCELLED),
        (BookingStatus.DISPUTED, BookingStatus.REFUNDED),
    ],
)
def test_valid_transitions(from_status: BookingStatus, to_status: BookingStatus) -> None:
    assert is_valid_booking_transition(from_status, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (BookingStatus.DRAFT, BookingStatus.CONFIRMED),
        (BookingStatus.REQUESTED, BookingStatus.CONFIRMED),
        (BookingStatus.REQUESTED, BookingStatus.DRAFT),
        (BookingStatus.QUOTATION_SENT, BookingStatus.REQUESTED),
        (BookingStatus.QUOTATION_SENT, BookingStatus.QUOTATION_SENT),
        (BookingStatus.CONFIRMED, BookingStatus.REQUESTED),
        (BookingStatus.CONFIRMED, BookingStatus.QUOTATION_SENT),
        (BookingStatus.CONFIRMED, BookingStatus.COMPLETED),
        (BookingStatus.DEPOSIT_PENDING, BookingStatus.CONFIRMED),
        (BookingStatus.IN_PROGRESS, BookingStatus.DEPOSIT_PENDING),
        (BookingStatus.DISPUTED, BookingStatus.REQUESTED),
        (BookingStatus.DISPUTED, BookingStatus.DISPUTED),
        (BookingStatus.CANCELLED, BookingStatus.DRAFT),
        (BookingStatus.REJECTED, BookingStatus.REQUESTED),
        (BookingStatus.REFUNDED, BookingStatus.REFUND_REQUESTED),
    ],
)
def test_invalid_transitions(from_status: BookingStatus, to_status: BookingStatus) -> None:
    assert not is_valid_booking_transition(from_status, to_status)


@pytest.mark.parametrize(
    "status",
    [BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.REFUNDED],
)
def test_terminal_statuses_have_no_outgoing_transitions(status: BookingStatus) -> None:
    assert status in TERMINAL_BOOKING_STATUSES
    assert BOOKING_STATUS_TRANSITIONS[status] == frozenset()


@pytest.mark.parametrize(
    "status",
    [BookingStatus.COMPLETED, BookingStatus.DISPUTED, BookingStatus.REFUND_REQUESTED],
)
def test_non_terminal_statuses_have_outgoing_transitions(status: BookingStatus) -> None:
    """Unlike the Phase 2 draft model, `completed` is not a dead end here — a
    customer can request a refund after the fact, and disputes/refund
    requests resolve back onto other statuses."""
    assert status not in TERMINAL_BOOKING_STATUSES
    assert BOOKING_STATUS_TRANSITIONS[status] != frozenset()


def test_every_status_is_reachable_from_the_initial_state() -> None:
    """Every declared status must be reachable by walking the transition
    graph from the initial (None) state — otherwise it's dead schema."""
    reachable: set[BookingStatus] = set()
    frontier = list(BOOKING_STATUS_TRANSITIONS[None])
    while frontier:
        status = frontier.pop()
        if status in reachable:
            continue
        reachable.add(status)
        frontier.extend(BOOKING_STATUS_TRANSITIONS.get(status, frozenset()))

    assert reachable == set(BookingStatus)
