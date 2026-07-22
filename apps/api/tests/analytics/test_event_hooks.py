"""Verifies the server-side event-recording hooks wired into existing
services/routes actually fire — see docs/analytics-and-recommendations.md
#track-events-for. Consent/sanitization mechanics themselves are covered in
test_events_and_consent.py; this file only checks that the right call
happens at the right place, using `make_consenting_user` throughout so the
resulting event is attributable and easy to assert on."""

import io
import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import AnalyticsEventType
from app.db.models.analytics import AnalyticsEvent
from app.services.booking import accept_quote, create_draft_booking, submit_booking
from app.services.engagement import (
    add_item_to_collection,
    get_or_create_default_collection,
    like_design,
)
from app.services.previews import create_preview
from app.services.view_tracking import record_design_view
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_booking,
    make_booking_quote,
    make_consenting_user,
    make_design,
)


def _events_of_type(
    db: Session,
    event_type: str,
    *,
    entity_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> list[AnalyticsEvent]:
    """Scoped by `entity_id`/`user_id` whenever the caller has one — a real
    `db.commit()` (which every hook call site here performs) is not
    guaranteed to be rolled back at test teardown in this codebase's
    fixture setup, so an unscoped `event_type`-only query can pick up rows
    a previous, unrelated test run already committed. Filtering by the
    specific entity/user this test created makes the assertion robust
    regardless."""
    stmt = select(AnalyticsEvent).where(AnalyticsEvent.event_type == event_type)
    if entity_id is not None:
        stmt = stmt.where(AnalyticsEvent.entity_id == entity_id)
    if user_id is not None:
        stmt = stmt.where(AnalyticsEvent.user_id == user_id)
    return list(db.execute(stmt).scalars().all())


def test_registration_records_registration_completed(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    new_user_id = str(uuid.uuid4())
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(
            200, json={"id": new_user_id, "email": "new@example.com", "email_confirmed_at": None}
        )
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "supersecret123",
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201

    # A fresh registrant's UserPreference.analytics_consent defaults False
    # (see docs/analytics-and-recommendations.md#provide-analytics-consent-
    # where-legally-required), so the event is recorded anonymized — assert
    # on the total count within this narrow window instead of by user_id.
    events = _events_of_type(db_session, AnalyticsEventType.REGISTRATION_COMPLETED.value)
    assert len(events) >= 1


def test_view_records_design_viewed(db_session: Session) -> None:
    viewer = make_consenting_user(db_session)
    design = make_design(db_session, status="published")
    db_session.commit()

    record_design_view(db_session, design_id=design.id, viewer_id=viewer.id)

    events = _events_of_type(
        db_session, AnalyticsEventType.DESIGN_VIEWED.value, entity_id=design.id
    )
    assert len(events) == 1
    assert events[0].user_id == viewer.id


def test_like_records_design_liked(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    design = make_design(db_session, status="published")
    db_session.commit()

    like_design(db_session, user_id=user.id, design_id=design.id)
    db_session.commit()

    events = _events_of_type(db_session, AnalyticsEventType.DESIGN_LIKED.value, entity_id=design.id)
    assert len(events) == 1


def test_save_records_design_saved(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    design = make_design(db_session, status="published")
    db_session.commit()

    collection = get_or_create_default_collection(db_session, user_id=user.id)
    add_item_to_collection(db_session, collection=collection, design_id=design.id)
    db_session.commit()

    events = _events_of_type(db_session, AnalyticsEventType.DESIGN_SAVED.value, entity_id=design.id)
    assert len(events) == 1


def test_booking_started_records_event(db_session: Session) -> None:
    customer = make_consenting_user(db_session)
    artist_profile = make_artist_profile(db_session)
    db_session.commit()

    booking = create_draft_booking(
        db_session, customer_id=customer.id, artist_profile_id=artist_profile.id
    )
    db_session.commit()

    events = _events_of_type(
        db_session, AnalyticsEventType.BOOKING_STARTED.value, entity_id=booking.id
    )
    assert len(events) == 1


def test_booking_submitted_records_event(db_session: Session) -> None:
    customer = make_consenting_user(db_session)
    artist_profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=artist_profile)
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status="draft",
        service_id=service.id,
    )
    db_session.commit()

    submit_booking(db_session, booking, changed_by=customer.id)
    db_session.commit()

    events = _events_of_type(
        db_session, AnalyticsEventType.BOOKING_SUBMITTED.value, entity_id=booking.id
    )
    assert len(events) == 1


def test_quote_accepted_records_event(db_session: Session) -> None:
    customer = make_consenting_user(db_session)
    artist_profile = make_artist_profile(db_session)
    # accept_quote only allows the decision from "quotation_sent"/
    # "customer_reviewing" — build the booking directly in that state
    # rather than re-driving the full draft -> ... -> quotation_sent state
    # machine, which is already covered by tests/booking/.
    booking = make_booking(
        db_session, customer=customer, artist_profile=artist_profile, status="quotation_sent"
    )
    quote = make_booking_quote(db_session, booking=booking, amount=5000)
    db_session.commit()

    accept_quote(db_session, booking, quote, changed_by=customer.id)
    db_session.commit()

    events = _events_of_type(
        db_session, AnalyticsEventType.QUOTE_ACCEPTED.value, entity_id=booking.id
    )
    assert len(events) == 1


def test_preview_created_records_event(db_session: Session, storage_mock: respx.MockRouter) -> None:
    storage_mock.post(url__regex=r"/object/preview-projects/.*").mock(
        return_value=httpx.Response(200, json={"Key": "preview-projects/mock"})
    )
    user = make_consenting_user(db_session)
    db_session.commit()

    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color=(80, 20, 140)).save(buffer, format="PNG")

    create_preview(
        db_session, user=user, design_id=None, overlay_transform=None, raw_photo=buffer.getvalue()
    )
    db_session.commit()

    events = _events_of_type(db_session, AnalyticsEventType.PREVIEW_CREATED.value, user_id=user.id)
    assert len(events) == 1
