"""Offset pagination + allow-listed sorting for admin data tables — see
docs/admin-dashboard.md#pagination-and-sorting.

Cursor (keyset) pagination (app/core/pagination.py) is the right fit for
public, deep, single-sort-order feeds; admin list views need the opposite —
a bounded, staff-facing dataset where clicking a column header to re-sort
is an explicit requirement (Phase 17). Offset pagination's usual downside
(cost grows with page depth) doesn't matter at admin scale, and it's the
only style that lets a client jump to page N or flip sort direction
without first holding a cursor minted for the old order.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / self.page_size))


def normalize_pagination(page: int | None, page_size: int | None) -> tuple[int, int]:
    """Clamps to sane bounds rather than erroring — an admin typing `page=0`
    or `page_size=99999` into a URL should just get page 1 / the max page
    size, not a 422."""
    return max(1, page or 1), max(1, min(page_size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE))


def resolve_sort_column(
    sort_by: str | None, *, columns: Mapping[str, Any], default_key: str
) -> tuple[str, Any]:
    """Validates `sort_by` against an explicit per-endpoint allow-list
    (never a raw column name built from client input) and returns the
    resolved key/column pair. `columns` is typed loosely (`Any`) because its
    values are ORM `InstrumentedAttribute`s, not plain `ColumnElement`s —
    both support `.asc()`/`.desc()`, which is all callers ever do with the
    result."""
    key = sort_by or default_key
    column = columns.get(key)
    if column is None:
        raise AppError(
            f"Cannot sort by '{key}'. Choose one of: {', '.join(sorted(columns))}.",
            status_code=422,
        )
    return key, column


def resolve_sort_direction(sort_dir: str | None) -> str:
    if sort_dir is None:
        return "desc"
    if sort_dir not in ("asc", "desc"):
        raise AppError("sort_dir must be 'asc' or 'desc'.", status_code=422)
    return sort_dir


def paginate[T](db: Session, stmt: Select[tuple[T]], *, page: int, page_size: int) -> Page[T]:
    """Runs one COUNT query (over the filtered-but-unordered statement) and
    one page query. `order_by(None)` strips any ORDER BY before counting —
    irrelevant to a row count and, for some sort expressions, not valid
    inside the COUNT subquery at all."""
    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    items = list(db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all())
    return Page(items=items, total=total, page=page, page_size=page_size)
