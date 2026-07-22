"""Request/response models for product analytics and recommendations — see
docs/analytics-and-recommendations.md.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.design import DesignSummaryOut


class ClientAnalyticsEventRequest(BaseModel):
    """Client-reported analytics events — see docs/analytics-and-
    recommendations.md#privacy-safe-analytics-event-schema. Only for events
    the server can't already observe itself (`app_opened`, `design_shared`
    — see `app/api/routes/analytics.py::_CLIENT_REPORTABLE_EVENT_TYPES`);
    every other event type in `AnalyticsEventType` is recorded automatically
    at its existing server-side call site and would be double-counted if a
    client could also report it here."""

    event_type: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    session_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class TrendingDesignOut(BaseModel):
    design: DesignSummaryOut
    score: float


class RecentlyViewedOut(BaseModel):
    items: list[DesignSummaryOut]


class RecommendedForYouOut(BaseModel):
    items: list[DesignSummaryOut]
    is_personalized: bool


class HomeFeedRecommendationOut(BaseModel):
    recently_viewed: list[DesignSummaryOut]
    recommended_for_you: list[DesignSummaryOut]
    trending: list[DesignSummaryOut]
    is_personalized: bool


class PopularArtistOut(BaseModel):
    artist_profile_id: uuid.UUID
    display_name: str
    rating_average: float
    rating_count: int
    follower_count: int
    score: float


class SearchQueryCountOut(BaseModel):
    query: str
    count: int


class SearchAnalyticsSummaryOut(BaseModel):
    window_days: int
    total_searches: int
    zero_result_searches: int
    zero_result_rate: float
    top_queries: list[SearchQueryCountOut]


class BookingConversionFunnelOut(BaseModel):
    window_days: int
    stage_counts: dict[str, int]
    stage_conversion_rates: dict[str, float | None]
    overall_conversion_rate: float | None
