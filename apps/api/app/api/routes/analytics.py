"""Product analytics and recommendations routes — see docs/analytics-and-
recommendations.md.

Similar-design recommendations already have their own endpoint —
`GET /designs/{id}/ai/similar` (Phase 20, `app/api/routes/ai.py`) — reused
as-is rather than duplicated here; see docs/analytics-and-recommendations
.md#similar-design-recommendations.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.enums import AnalyticsEventType
from app.db.session import get_db_session
from app.schemas.analytics import (
    ClientAnalyticsEventRequest,
    HomeFeedRecommendationOut,
    RecentlyViewedOut,
    RecommendedForYouOut,
)
from app.services.analytics.events import record_event
from app.services.analytics.recommendations import (
    get_category_based_recommendations,
    get_personalized_home_feed,
    get_recently_viewed_designs,
)
from app.services.design_summaries import summaries_for_designs

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Event types a client may self-report — deliberately excludes every event
# type the server already records at its own call site (design views/
# likes/saves, registration, artist views, booking/payment/subscription/AI-
# generation/preview events — see docs/analytics-and-recommendations.md
# #privacy-safe-analytics-event-schema). Only things with no server-side
# observation point at all belong here.
_CLIENT_REPORTABLE_EVENT_TYPES = {
    AnalyticsEventType.APP_OPENED.value,
    AnalyticsEventType.DESIGN_SHARED.value,
}


def _rate_limit() -> str:
    return get_settings().analytics_rate_limit


@router.post("/events", status_code=204)
@limiter.limit(_rate_limit())
def report_analytics_event(
    request: Request,
    payload: ClientAnalyticsEventRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    if payload.event_type not in _CLIENT_REPORTABLE_EVENT_TYPES:
        raise AppError(
            f"event_type must be one of: {', '.join(sorted(_CLIENT_REPORTABLE_EVENT_TYPES))}.",
            status_code=422,
        )
    record_event(
        db,
        event_type=payload.event_type,
        user_id=current.user.id,
        session_id=payload.session_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        properties=payload.properties,
    )
    db.commit()


@router.get("/recently-viewed", response_model=RecentlyViewedOut)
def get_my_recently_viewed(
    limit: int = 10,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RecentlyViewedOut:
    limit = max(1, min(limit, 50))
    designs = get_recently_viewed_designs(db, user_id=current.user.id, limit=limit)
    return RecentlyViewedOut(items=summaries_for_designs(db, designs))


@router.get("/recommended", response_model=RecommendedForYouOut)
def get_my_recommendations(
    limit: int = 10,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RecommendedForYouOut:
    limit = max(1, min(limit, 50))
    designs = get_category_based_recommendations(db, user_id=current.user.id, limit=limit)
    return RecommendedForYouOut(
        items=summaries_for_designs(db, designs), is_personalized=bool(designs)
    )


@router.get("/home-feed", response_model=HomeFeedRecommendationOut)
def get_my_home_feed(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> HomeFeedRecommendationOut:
    sections = get_personalized_home_feed(db, user_id=current.user.id)
    return HomeFeedRecommendationOut(
        recently_viewed=summaries_for_designs(db, sections.recently_viewed),
        recommended_for_you=summaries_for_designs(db, sections.recommended_for_you),
        trending=summaries_for_designs(db, sections.trending),
        is_personalized=sections.is_personalized,
    )
