"""Admin analytics views — see docs/analytics-and-recommendations.md#admin-
analytics-views.

Read-only reporting surfaces, all gated to `moderator`/`admin`/`super_admin`
— the same `_VIEW_ROLES` split every other admin-reporting route in this
codebase uses (e.g. `app/api/routes/admin_dashboard.py`). Nothing here
mutates anything, so there is no separate edit-role split.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.analytics import (
    BookingConversionFunnelOut,
    PopularArtistOut,
    SearchAnalyticsSummaryOut,
    SearchQueryCountOut,
    TrendingDesignOut,
)
from app.services.analytics.booking_analytics import get_booking_conversion_funnel
from app.services.analytics.recommendations import get_popular_artists, get_trending_designs
from app.services.analytics.search_analytics import get_search_analytics_summary
from app.services.design_summaries import summaries_for_designs

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")


@router.get("/trending-designs", response_model=list[TrendingDesignOut])
def list_trending_designs(
    window_days: int = 7,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[TrendingDesignOut]:
    limit = max(1, min(limit, 100))
    window_days = max(1, min(window_days, 365))
    scored = get_trending_designs(db, window_days=window_days, limit=limit)

    summaries = summaries_for_designs(db, [design for design, _score in scored])
    summary_by_id = {s.id: s for s in summaries}
    return [
        TrendingDesignOut(design=summary_by_id[design.id], score=score)
        for design, score in scored
        if design.id in summary_by_id
    ]


@router.get("/popular-artists", response_model=list[PopularArtistOut])
def list_popular_artists(
    window_days: int = 30,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[PopularArtistOut]:
    limit = max(1, min(limit, 100))
    window_days = max(1, min(window_days, 365))
    scored = get_popular_artists(db, window_days=window_days, limit=limit)

    contact_profiles = {
        p.user_id: p
        for p in db.execute(
            select(Profile).where(Profile.user_id.in_([artist.user_id for artist, _ in scored]))
        )
        .scalars()
        .all()
    }

    results: list[PopularArtistOut] = []
    for artist, score in scored:
        contact_profile = contact_profiles.get(artist.user_id)
        display_name = (
            artist.professional_name
            or artist.business_name
            or (contact_profile.display_name if contact_profile else None)
            or "Independent Artist"
        )
        results.append(
            PopularArtistOut(
                artist_profile_id=artist.id,
                display_name=display_name,
                rating_average=float(artist.rating_average),
                rating_count=artist.rating_count,
                follower_count=artist.follower_count,
                score=score,
            )
        )
    return results


@router.get("/search", response_model=SearchAnalyticsSummaryOut)
def get_search_analytics(
    window_days: int = 30,
    top_query_limit: int = 10,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> SearchAnalyticsSummaryOut:
    window_days = max(1, min(window_days, 365))
    top_query_limit = max(1, min(top_query_limit, 50))
    summary = get_search_analytics_summary(
        db, window_days=window_days, top_query_limit=top_query_limit
    )
    return SearchAnalyticsSummaryOut(
        window_days=window_days,
        total_searches=summary.total_searches,
        zero_result_searches=summary.zero_result_searches,
        zero_result_rate=summary.zero_result_rate,
        top_queries=[
            SearchQueryCountOut(query=query, count=count) for query, count in summary.top_queries
        ],
    )


@router.get("/booking-conversion", response_model=BookingConversionFunnelOut)
def get_booking_conversion(
    window_days: int = 30,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> BookingConversionFunnelOut:
    window_days = max(1, min(window_days, 365))
    funnel = get_booking_conversion_funnel(db, window_days=window_days)
    return BookingConversionFunnelOut(
        window_days=window_days,
        stage_counts=funnel.stage_counts,
        stage_conversion_rates=funnel.stage_conversion_rates,
        overall_conversion_rate=funnel.overall_conversion_rate,
    )
