"""`app/services/analytics/recommendations.py` — see docs/analytics-and-
recommendations.md."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.enums import AnalyticsEventType
from app.db.models.design import DesignCategory
from app.services.analytics.recommendations import (
    get_category_based_recommendations,
    get_personalized_home_feed,
    get_popular_artists,
    get_recently_viewed_designs,
    get_trending_designs,
)
from tests.db.factories import (
    make_analytics_event,
    make_artist_profile,
    make_category,
    make_consenting_user,
    make_design,
)


def test_trending_designs_ranks_by_weighted_recent_engagement(db_session: Session) -> None:
    saved_design = make_design(db_session, status="published")
    viewed_design = make_design(db_session, status="published")
    db_session.commit()

    # A single save (weight 5) should outrank three plain views (weight 3).
    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_SAVED.value,
        entity_type="design",
        entity_id=saved_design.id,
    )
    for _ in range(3):
        make_analytics_event(
            db_session,
            event_type=AnalyticsEventType.DESIGN_VIEWED.value,
            entity_type="design",
            entity_id=viewed_design.id,
        )
    db_session.commit()

    results = get_trending_designs(db_session, limit=10)
    ranked_ids = [design.id for design, _score in results]
    assert ranked_ids.index(saved_design.id) < ranked_ids.index(viewed_design.id)


def test_trending_designs_ignores_events_outside_the_window(db_session: Session) -> None:
    old_design = make_design(db_session, status="published")
    db_session.commit()
    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_SAVED.value,
        entity_type="design",
        entity_id=old_design.id,
        created_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.commit()

    results = get_trending_designs(db_session, window_days=7, limit=10)
    assert old_design.id not in [design.id for design, _score in results]


def test_trending_designs_excludes_unpublished_designs(db_session: Session) -> None:
    draft_design = make_design(db_session, status="draft")
    db_session.commit()
    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_SAVED.value,
        entity_type="design",
        entity_id=draft_design.id,
    )
    db_session.commit()

    results = get_trending_designs(db_session, limit=10)
    assert draft_design.id not in [design.id for design, _score in results]


def test_popular_artists_ranks_approved_artists_by_rating_and_views(
    db_session: Session,
) -> None:
    strong_artist = make_artist_profile(db_session)
    strong_artist.verification_status = "approved"
    strong_artist.rating_average = 4.9
    strong_artist.rating_count = 50
    db_session.add(strong_artist)

    weak_artist = make_artist_profile(db_session)
    weak_artist.verification_status = "approved"
    weak_artist.rating_average = 2.0
    weak_artist.rating_count = 2
    db_session.add(weak_artist)
    db_session.commit()

    results = get_popular_artists(db_session, limit=10)
    ranked_ids = [artist.id for artist, _score in results]
    assert ranked_ids.index(strong_artist.id) < ranked_ids.index(weak_artist.id)


def test_popular_artists_excludes_unapproved_artists(db_session: Session) -> None:
    unapproved = make_artist_profile(db_session)
    unapproved.verification_status = "submitted"
    db_session.add(unapproved)
    db_session.commit()

    results = get_popular_artists(db_session, limit=10)
    assert unapproved.id not in [artist.id for artist, _score in results]


def test_recently_viewed_orders_most_recent_first(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    older_design = make_design(db_session, status="published")
    newer_design = make_design(db_session, status="published")
    db_session.commit()

    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_VIEWED.value,
        user=user,
        entity_type="design",
        entity_id=older_design.id,
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_VIEWED.value,
        user=user,
        entity_type="design",
        entity_id=newer_design.id,
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.commit()

    results = get_recently_viewed_designs(db_session, user_id=user.id, limit=10)
    assert [d.id for d in results] == [newer_design.id, older_design.id]


def test_recently_viewed_returns_empty_for_a_user_with_no_history(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    db_session.commit()
    assert get_recently_viewed_designs(db_session, user_id=user.id) == []


def test_recently_viewed_returns_empty_without_a_user_or_session(db_session: Session) -> None:
    assert get_recently_viewed_designs(db_session) == []


def test_category_recommendations_suggest_designs_in_the_users_engaged_category(
    db_session: Session,
) -> None:
    user = make_consenting_user(db_session)
    category = make_category(db_session)
    engaged_design = make_design(db_session, status="published")
    recommended_design = make_design(db_session, status="published")
    db_session.commit()

    db_session.add_all(
        [
            DesignCategory(design_id=engaged_design.id, category_id=category.id),
            DesignCategory(design_id=recommended_design.id, category_id=category.id),
        ]
    )
    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_LIKED.value,
        user=user,
        entity_type="design",
        entity_id=engaged_design.id,
    )
    db_session.commit()

    results = get_category_based_recommendations(db_session, user_id=user.id, limit=10)
    result_ids = [d.id for d in results]
    assert recommended_design.id in result_ids
    # The design that generated the signal is never recommended back.
    assert engaged_design.id not in result_ids


def test_category_recommendations_empty_for_a_user_with_no_history(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    db_session.commit()
    assert get_category_based_recommendations(db_session, user_id=user.id) == []


def test_personalized_home_feed_falls_back_to_latest_for_a_brand_new_platform(
    db_session: Session,
) -> None:
    """No engagement history anywhere yet -- the fallback-for-new-users
    path (docs/analytics-and-recommendations.md#add-fallback-content-for-
    new-users) must still return non-empty trending content."""
    design = make_design(db_session, status="published")
    db_session.commit()

    # A generous section_limit, not the default 10 -- other tests in this
    # suite commit their own trending-worthy designs/events (this codebase's
    # test fixture does not roll back a `db.commit()`, only an un-flushed
    # change -- see tests/ai/test_jobs_queue.py's notes on this), so a tight
    # limit could push this test's own design out of the fallback list
    # purely due to unrelated leftover data, not a real behavior bug.
    sections = get_personalized_home_feed(db_session, section_limit=1000)

    assert sections.is_personalized is False
    assert design.id in [d.id for d in sections.trending]


def test_personalized_home_feed_is_personalized_for_a_user_with_history(
    db_session: Session,
) -> None:
    user = make_consenting_user(db_session)
    design = make_design(db_session, status="published")
    db_session.commit()

    make_analytics_event(
        db_session,
        event_type=AnalyticsEventType.DESIGN_VIEWED.value,
        user=user,
        entity_type="design",
        entity_id=design.id,
    )
    db_session.commit()

    sections = get_personalized_home_feed(db_session, user_id=user.id)

    assert sections.is_personalized is True
    assert design.id in [d.id for d in sections.recently_viewed]
