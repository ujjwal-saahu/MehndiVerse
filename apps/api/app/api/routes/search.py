"""Design search — see docs/design-search.md.

Mounted in app/main.py *before* app/api/routes/designs.py's
`/designs/{design_id}` route — `/designs/search` is a literal path that
would otherwise be captured by that dynamic segment (the same ordering
concern Phase 7 already resolved for `/designs/published` and
`/designs/home-feed`; see docs/design-gallery.md).
"""

import uuid
from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError
from app.core.search_sanitize import sanitize_search_query
from app.db.models.design import Design
from app.db.models.search import SearchEvent
from app.db.session import get_db_session
from app.schemas.design import DesignListOut, PageInfo
from app.schemas.search import SearchHistoryItemOut, SearchSuggestionOut
from app.services.design_summaries import summaries_for_designs
from app.services.search.base import SearchFilters, SearchSort
from app.services.search.factory import get_search_provider

router = APIRouter(prefix="/designs/search", tags=["search"])

_SORT_MODES = {"relevance", "newest", "popular", "most_saved"}
_VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
_VALID_BODY_PLACEMENTS = {"hand", "foot", "arm", "back", "other"}

_SUGGESTION_LIMIT = 8
_MIN_SUGGESTION_QUERY_LENGTH = 2
_HISTORY_LIMIT = 10
_HISTORY_OVERFETCH = 50
_MAX_CATEGORY_FILTERS = 20


def _rate_limit() -> str:
    return get_settings().search_rate_limit


def _designs_in_order(db: Session, design_ids: list[uuid.UUID]) -> list[Design]:
    """Preserves the search provider's ranking — `WHERE id IN (...)` alone
    would return rows in whatever order Postgres feels like."""
    if not design_ids:
        return []
    rows = db.execute(select(Design).where(Design.id.in_(design_ids))).scalars().all()
    by_id = {d.id: d for d in rows}
    return [by_id[design_id] for design_id in design_ids if design_id in by_id]


@router.get("", response_model=DesignListOut)
@limiter.limit(_rate_limit())
def search_designs(
    request: Request,
    q: str | None = None,
    category_id: list[uuid.UUID] = Query(default=[]),
    artist_id: uuid.UUID | None = None,
    is_premium: bool | None = None,
    difficulty_level: str | None = None,
    body_placement: str | None = None,
    sort: str = "relevance",
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignListOut:
    if sort not in _SORT_MODES:
        raise AppError(f"sort must be one of: {', '.join(sorted(_SORT_MODES))}", status_code=422)
    if difficulty_level is not None and difficulty_level not in _VALID_DIFFICULTIES:
        raise AppError(
            f"difficulty_level must be one of: {', '.join(sorted(_VALID_DIFFICULTIES))}",
            status_code=422,
        )
    if body_placement is not None and body_placement not in _VALID_BODY_PLACEMENTS:
        raise AppError(
            f"body_placement must be one of: {', '.join(sorted(_VALID_BODY_PLACEMENTS))}",
            status_code=422,
        )
    if len(category_id) > _MAX_CATEGORY_FILTERS:
        raise AppError(
            f"No more than {_MAX_CATEGORY_FILTERS} category filters may be combined.",
            status_code=422,
        )
    limit = max(1, min(limit, 100))

    query = sanitize_search_query(q)
    filters = SearchFilters(
        category_ids=tuple(category_id),
        artist_profile_id=artist_id,
        is_premium=is_premium,
        difficulty_level=difficulty_level,
        body_placement=body_placement,
    )

    provider = get_search_provider()
    try:
        page = provider.search(
            db,
            query=query,
            filters=filters,
            sort=cast(SearchSort, sort),
            cursor=cursor,
            limit=limit,
        )
    except InvalidCursorError as exc:
        raise AppError(str(exc), status_code=422) from exc

    designs = _designs_in_order(db, page.design_ids)
    items = summaries_for_designs(db, designs)

    # Search-analytics-event foundation: every search (keyword and/or
    # filters-only) is logged; only ones with an actual keyword ever surface
    # in "recent searches" (see get_search_history below). No caching header
    # here (unlike Phase 7's home-feed/list endpoints) — every request needs
    # to reach the backend so this event gets recorded, even for a query
    # that's byte-for-byte identical to a previous one.
    db.add(
        SearchEvent(
            user_id=current.user.id,
            query=query,
            filters={
                "category_ids": [str(c) for c in filters.category_ids],
                "artist_profile_id": (
                    str(filters.artist_profile_id) if filters.artist_profile_id else None
                ),
                "is_premium": filters.is_premium,
                "difficulty_level": filters.difficulty_level,
                "body_placement": filters.body_placement,
                "sort": sort,
            },
            result_count=len(items),
        )
    )
    db.commit()

    return DesignListOut(
        items=items,
        page_info=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.get("/suggestions", response_model=list[SearchSuggestionOut])
@limiter.limit(_rate_limit())
def get_search_suggestions(
    request: Request,
    q: str,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SearchSuggestionOut]:
    query = sanitize_search_query(q)
    if query is None or len(query) < _MIN_SUGGESTION_QUERY_LENGTH:
        return []

    provider = get_search_provider()
    hits = provider.suggest(db, query=query, limit=_SUGGESTION_LIMIT)
    return [SearchSuggestionOut(type=hit.type, id=hit.id, label=hit.label) for hit in hits]


@router.get("/history", response_model=list[SearchHistoryItemOut])
def get_search_history(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SearchHistoryItemOut]:
    rows = (
        db.execute(
            select(SearchEvent)
            .where(SearchEvent.user_id == current.user.id, SearchEvent.query.isnot(None))
            .order_by(SearchEvent.created_at.desc())
            .limit(_HISTORY_OVERFETCH)
        )
        .scalars()
        .all()
    )

    seen: set[str] = set()
    result: list[SearchHistoryItemOut] = []
    for row in rows:
        if row.query is None:
            continue
        key = row.query.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(SearchHistoryItemOut(id=row.id, query=row.query, created_at=row.created_at))
        if len(result) >= _HISTORY_LIMIT:
            break
    return result


@router.delete("/history", status_code=204)
def clear_search_history(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    db.execute(delete(SearchEvent).where(SearchEvent.user_id == current.user.id))
    db.commit()
