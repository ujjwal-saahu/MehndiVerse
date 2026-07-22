"""Search analytics — see docs/analytics-and-recommendations.md#search-
analytics.

Reads the pre-existing `SearchEvent` table (`app/db/models/search.py`,
Phase 8/9's search-history/analytics foundation) rather than a new event
stream — every search request already logs its query, filters, and result
count there. This module only adds aggregate reporting on top of data
that's already being collected.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.search import SearchEvent

DEFAULT_WINDOW_DAYS = 30
DEFAULT_TOP_QUERY_LIMIT = 10


class SearchAnalyticsSummary:
    def __init__(
        self,
        *,
        total_searches: int,
        zero_result_searches: int,
        top_queries: list[tuple[str, int]],
    ) -> None:
        self.total_searches = total_searches
        self.zero_result_searches = zero_result_searches
        self.top_queries = top_queries

    @property
    def zero_result_rate(self) -> float:
        if self.total_searches == 0:
            return 0.0
        return self.zero_result_searches / self.total_searches


def get_search_analytics_summary(
    db: Session,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    top_query_limit: int = DEFAULT_TOP_QUERY_LIMIT,
) -> SearchAnalyticsSummary:
    """`zero_result_rate` is the single most actionable search-quality
    metric a foundation needs: a consistently high rate points at either a
    catalog gap (nothing matches what people search for) or a search-
    provider relevance problem — either way, something staff should look
    at. `top_queries` only ever counts non-blank keyword searches (a
    filters-only search has no query text to rank)."""
    since = datetime.now(UTC) - timedelta(days=window_days)
    base = select(SearchEvent).where(SearchEvent.created_at >= since)

    total_searches = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    zero_result_searches = db.execute(
        select(func.count()).select_from(base.where(SearchEvent.result_count == 0).subquery())
    ).scalar_one()

    top_query_rows = db.execute(
        select(SearchEvent.query, func.count().label("count"))
        .where(
            SearchEvent.created_at >= since,
            SearchEvent.query.is_not(None),
            SearchEvent.query != "",
        )
        .group_by(SearchEvent.query)
        .order_by(func.count().desc())
        .limit(top_query_limit)
    ).all()

    return SearchAnalyticsSummary(
        total_searches=total_searches,
        zero_result_searches=zero_result_searches,
        top_queries=[(query, count) for query, count in top_query_rows],
    )
