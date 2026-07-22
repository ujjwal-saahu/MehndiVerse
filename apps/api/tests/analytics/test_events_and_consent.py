"""`app/services/analytics/events.py::record_event` — see docs/analytics-
and-recommendations.md#privacy-safe-analytics-event-schema and
#provide-analytics-consent-where-legally-required."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.analytics import AnalyticsEvent
from app.db.models.system import SystemSetting
from app.services.analytics.events import record_event
from app.services.analytics.flags import is_analytics_enabled
from tests.db.factories import make_consenting_user, make_design, make_user, make_user_preference


def test_record_event_stores_the_given_fields_for_a_consenting_user(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    design = make_design(db_session)
    db_session.commit()

    event = record_event(
        db_session,
        event_type="design_viewed",
        user_id=user.id,
        entity_type="design",
        entity_id=design.id,
        properties={"source": "gallery"},
    )
    db_session.commit()

    assert event is not None
    stored = db_session.get(AnalyticsEvent, event.id)
    assert stored is not None
    assert stored.event_type == "design_viewed"
    assert stored.user_id == user.id
    assert stored.entity_type == "design"
    assert stored.entity_id == design.id
    assert stored.properties == {"source": "gallery"}


def test_record_event_anonymizes_a_non_consenting_users_identity(db_session: Session) -> None:
    user = make_user(db_session)  # no UserPreference row -> not consented
    db_session.commit()

    event = record_event(db_session, event_type="design_viewed", user_id=user.id)
    db_session.commit()

    assert event is not None
    assert event.user_id is None


def test_record_event_anonymizes_when_consent_is_explicitly_false(db_session: Session) -> None:
    user = make_user(db_session)
    make_user_preference(db_session, user=user, analytics_consent=False)
    db_session.commit()

    event = record_event(db_session, event_type="design_viewed", user_id=user.id)
    db_session.commit()

    assert event is not None
    assert event.user_id is None


def test_record_event_preserves_session_id_for_anonymized_events(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()

    event = record_event(
        db_session, event_type="design_viewed", user_id=user.id, session_id="sess-abc"
    )
    db_session.commit()

    assert event is not None
    assert event.user_id is None
    assert event.session_id == "sess-abc"


def test_record_event_returns_none_and_records_nothing_when_globally_disabled(
    db_session: Session,
) -> None:
    db_session.add(SystemSetting(key="analytics.enabled", value={"enabled": False}))
    db_session.commit()

    user = make_consenting_user(db_session)
    db_session.commit()

    result = record_event(db_session, event_type="design_viewed", user_id=user.id)
    db_session.commit()

    assert result is None
    assert (
        db_session.execute(select(AnalyticsEvent).where(AnalyticsEvent.user_id == user.id)).first()
        is None
    )


def test_analytics_enabled_defaults_true_with_no_settings_row(db_session: Session) -> None:
    assert is_analytics_enabled(db_session) is True


def test_record_event_strips_denylisted_property_keys(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    db_session.commit()

    event = record_event(
        db_session,
        event_type="design_viewed",
        user_id=user.id,
        properties={"email": "someone@example.com", "safe_key": "kept"},
    )
    db_session.commit()

    assert event is not None
    assert event.properties == {"safe_key": "kept"}


def test_record_event_truncates_overly_long_property_values(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    db_session.commit()

    long_value = "x" * 500
    event = record_event(
        db_session, event_type="design_viewed", user_id=user.id, properties={"note": long_value}
    )
    db_session.commit()

    assert event is not None
    assert event.properties is not None
    assert len(event.properties["note"]) == 200
