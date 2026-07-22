"""Recommendation calculations — see docs/analytics-and-recommendations.md
for the documented logic behind each of these (the "document recommendation
logic" requirement is satisfied by that doc file plus the docstring on each
function below, not by the code alone).

Every calculation here reads `AnalyticsEvent` (and, for similar-design
recommendations, Phase 20's `DesignEmbedding` via `app/services/ai/
similarity.py` — reused, not reimplemented) and returns already-published,
non-deleted designs (or approved artist profiles) only; nothing here ever
surfaces draft/unpublished/unverified content through a recommendation
surface.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Case, case, func, select
from sqlalchemy.orm import Session

from app.db.enums import AnalyticsEventType, ArtistVerificationStatus, DesignStatus
from app.db.models.analytics import AnalyticsEvent
from app.db.models.artist import ArtistProfile
from app.db.models.design import Design, DesignCategory
from app.services.ai.similarity import find_similar_designs

DEFAULT_TRENDING_WINDOW_DAYS = 7
DEFAULT_POPULAR_ARTIST_WINDOW_DAYS = 30
DEFAULT_RECOMMENDATION_LIMIT = 10
DEFAULT_HOME_FEED_SECTION_LIMIT = 10
CATEGORY_HISTORY_LOOKBACK_DAYS = 90
TOP_CATEGORIES_CONSIDERED = 3

# Engagement weights shared by trending-design scoring — a save signals
# stronger intent than a like, which signals stronger intent than a view.
# This is the single source of truth for "how popularity is computed" from
# raw events; see docs/analytics-and-recommendations.md#trending-design-
# calculation.
_ENGAGEMENT_WEIGHTS: dict[str, int] = {
    AnalyticsEventType.DESIGN_VIEWED.value: 1,
    AnalyticsEventType.DESIGN_LIKED.value: 3,
    AnalyticsEventType.DESIGN_SAVED.value: 5,
}


def _engagement_score_expression() -> Case[int]:
    return case(_ENGAGEMENT_WEIGHTS, value=AnalyticsEvent.event_type, else_=0)


def _published_designs_by_id(db: Session, design_ids: list[uuid.UUID]) -> dict[uuid.UUID, Design]:
    if not design_ids:
        return {}
    rows = (
        db.execute(
            select(Design).where(
                Design.id.in_(design_ids),
                Design.status == DesignStatus.PUBLISHED.value,
                Design.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    return {d.id: d for d in rows}


def get_trending_designs(
    db: Session,
    *,
    window_days: int = DEFAULT_TRENDING_WINDOW_DAYS,
    limit: int = DEFAULT_RECOMMENDATION_LIMIT,
) -> list[tuple[Design, float]]:
    """ "Trending" = weighted engagement *within the last `window_days`*,
    not lifetime popularity — see docs/analytics-and-recommendations.md
    #trending-design-calculation for why this is deliberately distinct from
    `app/api/routes/designs.py::get_home_feed`'s pre-existing "trending"
    section (a simple lifetime `view_count DESC` sort, unaffected by this
    phase). A design published years ago with a huge lifetime view count
    isn't "trending" today; a design that suddenly got a burst of views
    this week is, even with a small lifetime total."""
    since = datetime.now(UTC) - timedelta(days=window_days)
    score = _engagement_score_expression()
    rows = db.execute(
        select(AnalyticsEvent.entity_id, func.sum(score).label("score"))
        .where(
            AnalyticsEvent.entity_type == "design",
            AnalyticsEvent.event_type.in_(_ENGAGEMENT_WEIGHTS),
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.entity_id.is_not(None),
        )
        .group_by(AnalyticsEvent.entity_id)
        .order_by(func.sum(score).desc())
        .limit(limit * 2)  # overfetch: some scored designs may since be unpublished/deleted
    ).all()

    designs_by_id = _published_designs_by_id(db, [row.entity_id for row in rows])
    results: list[tuple[Design, float]] = []
    for entity_id, score_value in rows:
        design = designs_by_id.get(entity_id)
        if design is not None:
            results.append((design, float(score_value)))
        if len(results) >= limit:
            break
    return results


def get_popular_artists(
    db: Session,
    *,
    window_days: int = DEFAULT_POPULAR_ARTIST_WINDOW_DAYS,
    limit: int = DEFAULT_RECOMMENDATION_LIMIT,
) -> list[tuple[ArtistProfile, float]]:
    """Blends a recency signal (`artist_viewed` events in the last
    `window_days` — a longer window than trending designs, since a good
    artist's reputation builds and stays relevant over a longer horizon
    than a single design's viral moment) with the durable trust signals
    this codebase already maintains on `ArtistProfile` itself: `rating_
    average` and `follower_count`. See docs/analytics-and-recommendations
    .md#popular-artist-calculation for the exact formula and why each term
    is weighted the way it is."""
    since = datetime.now(UTC) - timedelta(days=window_days)
    recent_views_subquery = (
        select(
            AnalyticsEvent.entity_id.label("artist_profile_id"),
            func.count().label("recent_view_count"),
        )
        .where(
            AnalyticsEvent.entity_type == "artist_profile",
            AnalyticsEvent.event_type == AnalyticsEventType.ARTIST_VIEWED.value,
            AnalyticsEvent.created_at >= since,
        )
        .group_by(AnalyticsEvent.entity_id)
        .subquery()
    )

    recent_views_column = func.coalesce(recent_views_subquery.c.recent_view_count, 0)
    # rating_average (0..5) * ln(1 + rating_count) rewards both quality and
    # a track record of *enough* reviews to trust that rating; follower_
    # count and recent profile views are lighter-weight popularity signals
    # added on top, not the dominant term.
    score = (
        (ArtistProfile.rating_average * func.ln(ArtistProfile.rating_count + 1))
        + (ArtistProfile.follower_count * 0.5)
        + (recent_views_column * 1.0)
    ).label("score")

    rows = db.execute(
        select(ArtistProfile, score)
        .outerjoin(
            recent_views_subquery,
            recent_views_subquery.c.artist_profile_id == ArtistProfile.id,
        )
        .where(
            ArtistProfile.verification_status == ArtistVerificationStatus.APPROVED.value,
            ArtistProfile.deleted_at.is_(None),
        )
        .order_by(score.desc())
        .limit(limit)
    ).all()
    return [(profile, float(score_value)) for profile, score_value in rows]


def get_recently_viewed_designs(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    session_id: str | None = None,
    limit: int = DEFAULT_RECOMMENDATION_LIMIT,
) -> list[Design]:
    """Reads back a viewer's own `design_viewed` events, most recent first,
    deduplicated per design. If the viewer never consented to identified
    analytics (see `events.py::record_event`), their prior `design_viewed`
    events were stored anonymized (no `user_id`) and are unreachable by
    `user_id` here — an intentional consequence of taking consent
    seriously, not a bug: a non-consenting user simply gets no server-side
    "recently viewed" personalization (a client may still keep its own
    local view history, entirely outside this API)."""
    if user_id is None and session_id is None:
        return []

    filters = [
        AnalyticsEvent.entity_type == "design",
        AnalyticsEvent.event_type == AnalyticsEventType.DESIGN_VIEWED.value,
    ]
    filters.append(
        AnalyticsEvent.user_id == user_id
        if user_id is not None
        else AnalyticsEvent.session_id == session_id
    )

    last_viewed_subquery = (
        select(
            AnalyticsEvent.entity_id.label("design_id"),
            func.max(AnalyticsEvent.created_at).label("last_viewed_at"),
        )
        .where(*filters, AnalyticsEvent.entity_id.is_not(None))
        .group_by(AnalyticsEvent.entity_id)
        .order_by(func.max(AnalyticsEvent.created_at).desc())
        .limit(limit * 2)
        .subquery()
    )
    ordered_ids = list(
        db.execute(
            select(last_viewed_subquery.c.design_id).order_by(
                last_viewed_subquery.c.last_viewed_at.desc()
            )
        )
        .scalars()
        .all()
    )

    designs_by_id = _published_designs_by_id(db, ordered_ids)
    ordered_designs = [designs_by_id[d_id] for d_id in ordered_ids if d_id in designs_by_id]
    return ordered_designs[:limit]


def _top_engaged_category_ids(
    db: Session, *, user_id: uuid.UUID, lookback_days: int
) -> tuple[list[uuid.UUID], set[uuid.UUID]]:
    """Returns (top category ids the user has engaged with, the set of
    design ids behind that engagement — so callers can exclude designs the
    user has already seen from the recommendations built on top)."""
    since = datetime.now(UTC) - timedelta(days=lookback_days)
    score = _engagement_score_expression()
    events = db.execute(
        select(AnalyticsEvent.entity_id, AnalyticsEvent.event_type).where(
            AnalyticsEvent.entity_type == "design",
            AnalyticsEvent.user_id == user_id,
            AnalyticsEvent.event_type.in_(_ENGAGEMENT_WEIGHTS),
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.entity_id.is_not(None),
        )
    ).all()
    engaged_design_ids = {row.entity_id for row in events}
    if not engaged_design_ids:
        return [], set()

    rows = db.execute(
        select(DesignCategory.category_id, func.sum(score))
        .select_from(AnalyticsEvent)
        .join(DesignCategory, DesignCategory.design_id == AnalyticsEvent.entity_id)
        .where(
            AnalyticsEvent.entity_type == "design",
            AnalyticsEvent.user_id == user_id,
            AnalyticsEvent.event_type.in_(_ENGAGEMENT_WEIGHTS),
            AnalyticsEvent.created_at >= since,
        )
        .group_by(DesignCategory.category_id)
        .order_by(func.sum(score).desc())
        .limit(TOP_CATEGORIES_CONSIDERED)
    ).all()
    return [row[0] for row in rows], engaged_design_ids


def get_category_based_recommendations(
    db: Session,
    *,
    user_id: uuid.UUID,
    lookback_days: int = CATEGORY_HISTORY_LOOKBACK_DAYS,
    limit: int = DEFAULT_RECOMMENDATION_LIMIT,
) -> list[Design]:
    """Infers up to `TOP_CATEGORIES_CONSIDERED` categories the user engages
    with most (weighted the same way as [trending](#trending-design-
    calculation): view=1/like=3/save=5, over `lookback_days`), then
    recommends other published designs in those categories the user hasn't
    already interacted with, ordered by lifetime `like_count` — a simple,
    explainable "people who liked X also tend to like other things in the
    same category" heuristic, not a trained collaborative-filtering model.
    Returns an empty list for a user with no engagement history at all —
    callers fall back to trending/latest content (see docs/analytics-and-
    recommendations.md#add-fallback-content-for-new-users)."""
    category_ids, exclude_design_ids = _top_engaged_category_ids(
        db, user_id=user_id, lookback_days=lookback_days
    )
    if not category_ids:
        return []

    stmt = (
        select(Design)
        .join(DesignCategory, DesignCategory.design_id == Design.id)
        .where(
            DesignCategory.category_id.in_(category_ids),
            Design.status == DesignStatus.PUBLISHED.value,
            Design.deleted_at.is_(None),
        )
        .order_by(Design.like_count.desc(), Design.id.desc())
        .limit(limit)
    )
    if exclude_design_ids:
        stmt = stmt.where(Design.id.not_in(exclude_design_ids))
    rows = db.execute(stmt).scalars().unique().all()
    return list(rows)


def get_similar_designs(
    db: Session, *, design_id: uuid.UUID, limit: int = DEFAULT_RECOMMENDATION_LIMIT
) -> list[tuple[uuid.UUID, float]]:
    """Similar-design recommendations are Phase 20's embedding-based
    `find_similar_designs` — reused verbatim, not reimplemented. See
    docs/ai-foundation.md#similar-design-search."""
    return find_similar_designs(db, design_id=design_id, limit=limit)


class HomeFeedSections:
    """Plain container (not a Pydantic schema — that lives in
    app/schemas/analytics.py) for the three sections a personalized home
    feed blends together."""

    def __init__(
        self,
        *,
        recently_viewed: list[Design],
        recommended_for_you: list[Design],
        trending: list[Design],
        is_personalized: bool,
    ) -> None:
        self.recently_viewed = recently_viewed
        self.recommended_for_you = recommended_for_you
        self.trending = trending
        self.is_personalized = is_personalized


def get_personalized_home_feed(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    session_id: str | None = None,
    section_limit: int = DEFAULT_HOME_FEED_SECTION_LIMIT,
) -> HomeFeedSections:
    """The "basic personalized home feed" — see docs/analytics-and-
    recommendations.md#basic-personalized-home-feed. Three sections:

    - `recently_viewed`: this viewer's own recent `design_viewed` history.
    - `recommended_for_you`: category-based recommendations from their
      engagement history (empty for a guest — category recommendations
      require a `user_id`, not just a `session_id`).
    - `trending`: always populated (time-windowed engagement, see
      `get_trending_designs`) — this is what a brand new user with no
      history at all sees in every section, which is exactly the "fallback
      content for new users" requirement: nobody ever gets an empty feed.

    `is_personalized` tells a client whether `recently_viewed`/
    `recommended_for_you` actually reflect this viewer, or are empty
    fallback-only sections.
    """
    recently_viewed = get_recently_viewed_designs(
        db, user_id=user_id, session_id=session_id, limit=section_limit
    )
    recommended_for_you = (
        get_category_based_recommendations(db, user_id=user_id, limit=section_limit)
        if user_id is not None
        else []
    )
    trending = [design for design, _score in get_trending_designs(db, limit=section_limit)]

    if not trending:
        # A brand new platform (or a quiet window) has no trending signal
        # yet either — fall back further, to the newest published designs,
        # so the feed is never empty even on day one. See docs/analytics-
        # and-recommendations.md#add-fallback-content-for-new-users.
        trending = list(
            db.execute(
                select(Design)
                .where(Design.status == DesignStatus.PUBLISHED.value, Design.deleted_at.is_(None))
                .order_by(Design.created_at.desc(), Design.id.desc())
                .limit(section_limit)
            )
            .scalars()
            .all()
        )

    return HomeFeedSections(
        recently_viewed=recently_viewed,
        recommended_for_you=recommended_for_you,
        trending=trending,
        is_personalized=bool(recently_viewed or recommended_for_you),
    )
