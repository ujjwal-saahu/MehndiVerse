"""PostgreSQL full-text search implementation of `SearchProvider` — see
docs/design-search.md#postgresql-full-text-search.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, and_, func, literal, select, tuple_
from sqlalchemy.orm import Session, aliased

from app.core.pagination import decode_cursor, encode_cursor
from app.db.enums import DesignStatus
from app.db.models.artist import ArtistProfile
from app.db.models.design import Category, Design, DesignCategory

from .base import SearchFilters, SearchPage, SearchProvider, SearchSort, SuggestionHit

_RANK_PRECISION = 10


def _apply_category_filters(db: Session, stmt: Any, category_ids: tuple[uuid.UUID, ...]) -> Any:
    """AND across taxonomy axes, OR within one — picking both "Bridal" and
    "Beginner Friendly" should require both, but picking two `occasion`
    categories should require either. See
    docs/design-search.md#category-filter-semantics."""
    if not category_ids:
        return stmt
    rows = db.execute(
        select(Category.id, Category.category_type).where(Category.id.in_(category_ids))
    ).all()
    by_type: dict[str, list[uuid.UUID]] = {}
    for category_id, category_type in rows:
        by_type.setdefault(category_type, []).append(category_id)
    for ids in by_type.values():
        alias = aliased(DesignCategory)
        stmt = stmt.join(alias, and_(alias.design_id == Design.id, alias.category_id.in_(ids)))
    return stmt


def _order_and_cursor_columns(
    sort: SearchSort, rank_col: ColumnElement[float]
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    if sort == "relevance":
        return (rank_col.desc(), Design.id.desc()), (rank_col, Design.id)
    if sort == "popular":
        return (Design.view_count.desc(), Design.id.desc()), (Design.view_count, Design.id)
    if sort == "most_saved":
        return (Design.save_count.desc(), Design.id.desc()), (Design.save_count, Design.id)
    return (Design.created_at.desc(), Design.id.desc()), (Design.created_at, Design.id)


def _cursor_sort_value(design: Design, sort: SearchSort, rank: float) -> str:
    if sort == "relevance":
        return f"{rank:.{_RANK_PRECISION}f}"
    if sort == "popular":
        return str(design.view_count)
    if sort == "most_saved":
        return str(design.save_count)
    return design.created_at.isoformat()


def _parse_cursor_value(sort: SearchSort, raw_value: str) -> datetime | int | float:
    if sort == "relevance":
        return float(raw_value)
    if sort in ("popular", "most_saved"):
        return int(raw_value)
    return datetime.fromisoformat(raw_value)


class PostgresFullTextSearchProvider(SearchProvider):
    def search(
        self,
        db: Session,
        *,
        query: str | None,
        filters: SearchFilters,
        sort: SearchSort,
        cursor: str | None,
        limit: int,
    ) -> SearchPage:
        # Relevance ranking needs something to rank against — fall back to
        # newest when no keyword was given, same idea as Phase 7's
        # trending-without-a-query fallback.
        effective_sort: SearchSort = "newest" if (sort == "relevance" and not query) else sort

        rank_col: ColumnElement[float] = literal(0.0)
        stmt = select(Design).where(
            Design.status == DesignStatus.PUBLISHED.value, Design.deleted_at.is_(None)
        )

        if query:
            ts_query = func.websearch_to_tsquery("english", query)
            stmt = stmt.where(Design.search_vector.op("@@")(ts_query))
            rank_col = func.ts_rank(Design.search_vector, ts_query)

        if filters.artist_profile_id is not None:
            stmt = stmt.where(Design.artist_profile_id == filters.artist_profile_id)
        if filters.is_premium is not None:
            stmt = stmt.where(Design.is_premium.is_(filters.is_premium))
        if filters.difficulty_level is not None:
            stmt = stmt.where(Design.difficulty_level == filters.difficulty_level)
        if filters.body_placement is not None:
            stmt = stmt.where(Design.body_placement == filters.body_placement)

        stmt = _apply_category_filters(db, stmt, filters.category_ids)

        order_cols, cursor_cols = _order_and_cursor_columns(effective_sort, rank_col)
        if cursor is not None:
            decoded = decode_cursor(cursor, expected_sort=effective_sort)
            cursor_value = _parse_cursor_value(effective_sort, decoded.sort_value)
            stmt = stmt.where(
                tuple_(*cursor_cols) < tuple_(literal(cursor_value), literal(decoded.id))
            )

        stmt = stmt.order_by(*order_cols).limit(limit + 1)

        designs = list(db.execute(stmt).scalars().all())
        has_more = len(designs) > limit
        page = designs[:limit]

        next_cursor = None
        if has_more and page:
            last = page[-1]
            # Recomputing the rank for just the cursor row is cheap (single
            # row, same GIN-narrowed match) and keeps the provider from
            # needing to project an extra column through the whole result set.
            last_rank = 0.0
            if effective_sort == "relevance" and query:
                last_rank = db.execute(
                    select(
                        func.ts_rank(
                            Design.search_vector, func.websearch_to_tsquery("english", query)
                        )
                    ).where(Design.id == last.id)
                ).scalar_one()
            next_cursor = encode_cursor(
                sort=effective_sort,
                sort_value=_cursor_sort_value(last, effective_sort, last_rank),
                id_=last.id,
            )

        return SearchPage(
            design_ids=[d.id for d in page], next_cursor=next_cursor, has_more=has_more
        )

    def suggest(self, db: Session, *, query: str, limit: int) -> list[SuggestionHit]:
        pattern = f"{query.lower()}%"

        design_rows = db.execute(
            select(Design.id, Design.title)
            .where(
                Design.status == DesignStatus.PUBLISHED.value,
                Design.deleted_at.is_(None),
                func.lower(Design.title).like(pattern),
            )
            .order_by(Design.view_count.desc())
            .limit(limit)
        ).all()
        category_rows = db.execute(
            select(Category.id, Category.name)
            .where(Category.is_active.is_(True), func.lower(Category.name).like(pattern))
            .order_by(Category.sort_order)
            .limit(limit)
        ).all()
        artist_rows = db.execute(
            select(ArtistProfile.id, ArtistProfile.business_name)
            .where(
                ArtistProfile.business_name.isnot(None),
                func.lower(ArtistProfile.business_name).like(pattern),
            )
            .limit(limit)
        ).all()

        hits: list[SuggestionHit] = [
            SuggestionHit(type="design", id=row.id, label=row.title) for row in design_rows
        ]
        hits += [SuggestionHit(type="category", id=row.id, label=row.name) for row in category_rows]
        hits += [
            SuggestionHit(type="artist", id=row.id, label=row.business_name)
            for row in artist_rows
            if row.business_name
        ]
        return hits[:limit]
