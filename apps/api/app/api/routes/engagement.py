"""Likes and quick-saves — see docs/engagement-and-collections.md.

Mounted in app/main.py *before* app/api/routes/designs.py's
`/designs/{design_id}` route — `/designs/saved` is a literal path that would
otherwise be captured by that dynamic segment (the same ordering concern
Phases 7/8 already resolved for `/designs/published` and `/designs/search`).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import DesignStatus
from app.db.models.design import Design
from app.db.models.engagement import CollectionItem
from app.db.session import get_db_session
from app.schemas.design import DesignListOut, PageInfo
from app.schemas.engagement import LikeStatusOut, SaveStatusOut
from app.services.design_summaries import summaries_for_designs
from app.services.engagement import (
    add_item_to_collection,
    get_default_collection,
    get_or_create_default_collection,
    like_design,
    remove_item_from_collection,
    unlike_design,
)

router = APIRouter(prefix="/designs", tags=["engagement"])

_SAVED_SORT = "saved"


def _get_published_design_or_404(db: Session, design_id: uuid.UUID) -> Design:
    """Liking/saving only applies to designs a stranger could otherwise
    discover — an unpublished design's id isn't a valid like/save target
    (mirrors the 404-not-403 visibility-leak precedent in designs.py)."""
    design = db.get(Design, design_id)
    if (
        design is None
        or design.deleted_at is not None
        or design.status != DesignStatus.PUBLISHED.value
    ):
        raise AppError("Design not found.", status_code=404)
    return design


@router.post("/{design_id}/like", response_model=LikeStatusOut)
def like(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> LikeStatusOut:
    design = _get_published_design_or_404(db, design_id)
    like_design(db, user_id=current.user.id, design_id=design.id)
    db.commit()
    db.refresh(design)
    return LikeStatusOut(liked=True, like_count=design.like_count)


@router.delete("/{design_id}/like", response_model=LikeStatusOut)
def unlike(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> LikeStatusOut:
    design = _get_published_design_or_404(db, design_id)
    unlike_design(db, user_id=current.user.id, design_id=design.id)
    db.commit()
    db.refresh(design)
    return LikeStatusOut(liked=False, like_count=design.like_count)


@router.post("/{design_id}/save", response_model=SaveStatusOut)
def save(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SaveStatusOut:
    design = _get_published_design_or_404(db, design_id)
    collection = get_or_create_default_collection(db, user_id=current.user.id)
    add_item_to_collection(db, collection=collection, design_id=design.id)
    db.commit()
    db.refresh(design)
    return SaveStatusOut(saved=True, save_count=design.save_count)


@router.delete("/{design_id}/save", response_model=SaveStatusOut)
def unsave(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SaveStatusOut:
    design = _get_published_design_or_404(db, design_id)
    collection = get_default_collection(db, user_id=current.user.id)
    if collection is not None:
        remove_item_from_collection(db, collection=collection, design_id=design.id)
    db.commit()
    db.refresh(design)
    return SaveStatusOut(saved=False, save_count=design.save_count)


@router.get("/saved", response_model=DesignListOut)
def list_saved_designs(
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignListOut:
    limit = max(1, min(limit, 100))
    collection = get_default_collection(db, user_id=current.user.id)
    if collection is None:
        return DesignListOut(items=[], page_info=PageInfo(next_cursor=None, has_more=False))

    stmt = (
        select(Design)
        .join(CollectionItem, CollectionItem.design_id == Design.id)
        .where(CollectionItem.collection_id == collection.id, Design.deleted_at.is_(None))
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_SAVED_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_added_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(CollectionItem.added_at, Design.id)
            < tuple_(literal(cursor_added_at), literal(decoded.id))
        )

    stmt = stmt.order_by(CollectionItem.added_at.desc(), Design.id.desc()).limit(limit + 1)

    rows = list(db.execute(stmt.add_columns(CollectionItem.added_at)).all())
    has_more = len(rows) > limit
    page = rows[:limit]

    next_cursor = None
    if has_more and page:
        last_design, last_added_at = page[-1]
        next_cursor = encode_cursor(
            sort=_SAVED_SORT, sort_value=last_added_at.isoformat(), id_=last_design.id
        )

    designs = [design for design, _added_at in page]
    return DesignListOut(
        items=summaries_for_designs(db, designs),
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )
