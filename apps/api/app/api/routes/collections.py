"""Collections — see docs/engagement-and-collections.md.

Route ordering within this file matters: `/collections/{id}/items/reorder`
is registered before `/collections/{id}/items/{design_id}` so a `PUT` to the
reorder path can never be captured by the parametrized delete-by-design-id
pattern, mirroring the literal-vs-parametrized caution from Phases 7/8
(distinct HTTP methods make an actual collision unlikely here, but the
convention is cheap to keep consistent).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError, AuthorizationError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import DesignStatus
from app.db.models.design import Design
from app.db.models.engagement import Collection, CollectionItem
from app.db.session import get_db_session
from app.schemas.design import PageInfo
from app.schemas.engagement import (
    CollectionCreateRequest,
    CollectionItemAddRequest,
    CollectionItemsOut,
    CollectionItemsReorderRequest,
    CollectionListOut,
    CollectionOut,
    CollectionUpdateRequest,
)
from app.services.design_summaries import batch_primary_images, summaries_for_designs, thumbnail_url
from app.services.engagement import (
    add_item_to_collection,
    remove_item_from_collection,
    reorder_collection_items,
    resolve_cover_urls,
)

router = APIRouter(prefix="/collections", tags=["collections"])

_COLLECTIONS_SORT = "collections"
_ITEMS_SORT = "items"


def _get_collection_or_404(db: Session, collection_id: uuid.UUID) -> Collection:
    collection = db.get(Collection, collection_id)
    if collection is None or collection.deleted_at is not None:
        raise AppError("Collection not found.", status_code=404)
    return collection


def _require_viewable(collection: Collection, current: AuthenticatedUser) -> None:
    """404s (not 403) if a non-owner can't see a private collection, so a
    stranger can't distinguish "exists but private" from "doesn't exist" —
    same principle as designs.py's visibility gate."""
    is_owner = collection.user_id == current.user.id
    if not is_owner and collection.is_private:
        raise AppError("Collection not found.", status_code=404)


def _require_owner(collection: Collection, current: AuthenticatedUser) -> None:
    if collection.user_id != current.user.id:
        raise AuthorizationError("You do not own this collection.")


def _collections_out(
    db: Session, collections: list[Collection], *, current_user_id: uuid.UUID
) -> list[CollectionOut]:
    if not collections:
        return []
    cover_by_collection = resolve_cover_urls(db, collections)
    cover_design_ids = [cid for cid in cover_by_collection.values() if cid is not None]
    images_by_design = batch_primary_images(db, cover_design_ids)
    count_rows = db.execute(
        select(CollectionItem.collection_id, func.count(CollectionItem.id))
        .where(CollectionItem.collection_id.in_([c.id for c in collections]))
        .group_by(CollectionItem.collection_id)
    ).all()
    counts: dict[uuid.UUID, int] = {collection_id: count for collection_id, count in count_rows}
    out = []
    for collection in collections:
        cover_design_id = cover_by_collection.get(collection.id)
        cover_url = (
            thumbnail_url(images_by_design.get(cover_design_id))
            if cover_design_id is not None
            else None
        )
        out.append(
            CollectionOut(
                id=collection.id,
                name=collection.name,
                description=collection.description,
                is_default=collection.is_default,
                is_private=collection.is_private,
                is_owner=collection.user_id == current_user_id,
                cover_image_url=cover_url,
                item_count=counts.get(collection.id, 0),
                created_at=collection.created_at,
                updated_at=collection.updated_at,
            )
        )
    return out


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(
    payload: CollectionCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionOut:
    existing = db.execute(
        select(Collection.id).where(
            Collection.user_id == current.user.id,
            Collection.name == payload.name,
            Collection.deleted_at.is_(None),
        )
    ).first()
    if existing is not None:
        raise AppError("You already have a collection with this name.", status_code=409)

    collection = Collection(
        user_id=current.user.id,
        name=payload.name,
        description=payload.description,
        is_private=payload.is_private,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return _collections_out(db, [collection], current_user_id=current.user.id)[0]


@router.get("", response_model=CollectionListOut)
def list_my_collections(
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionListOut:
    limit = max(1, min(limit, 100))
    stmt = select(Collection).where(
        Collection.user_id == current.user.id, Collection.deleted_at.is_(None)
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_COLLECTIONS_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(Collection.created_at, Collection.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(Collection.created_at.desc(), Collection.id.desc()).limit(limit + 1)

    collections = list(db.execute(stmt).scalars().all())
    has_more = len(collections) > limit
    page = collections[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_COLLECTIONS_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    return CollectionListOut(
        items=_collections_out(db, page, current_user_id=current.user.id),
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionOut:
    collection = _get_collection_or_404(db, collection_id)
    _require_viewable(collection, current)
    return _collections_out(db, [collection], current_user_id=current.user.id)[0]


@router.patch("/{collection_id}", response_model=CollectionOut)
def update_collection(
    collection_id: uuid.UUID,
    payload: CollectionUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionOut:
    collection = _get_collection_or_404(db, collection_id)
    _require_owner(collection, current)

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != collection.name:
        clash = db.execute(
            select(Collection.id).where(
                Collection.user_id == current.user.id,
                Collection.name == updates["name"],
                Collection.deleted_at.is_(None),
                Collection.id != collection.id,
            )
        ).first()
        if clash is not None:
            raise AppError("You already have a collection with this name.", status_code=409)
    if "cover_design_id" in updates and updates["cover_design_id"] is not None:
        cover_design = db.get(Design, updates["cover_design_id"])
        if (
            cover_design is None
            or cover_design.deleted_at is not None
            or cover_design.status != DesignStatus.PUBLISHED.value
        ):
            raise AppError("cover_design_id must be a published design.", status_code=422)

    for field, value in updates.items():
        setattr(collection, field, value)

    db.add(collection)
    db.commit()
    db.refresh(collection)
    return _collections_out(db, [collection], current_user_id=current.user.id)[0]


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    collection = _get_collection_or_404(db, collection_id)
    _require_owner(collection, current)
    if collection.is_default:
        raise AppError(
            'Your default "Saved Designs" collection can\'t be deleted.', status_code=400
        )

    collection.deleted_at = datetime.now(UTC)
    db.add(collection)
    db.commit()


@router.put("/{collection_id}/items/reorder", response_model=CollectionItemsOut)
def reorder_items(
    collection_id: uuid.UUID,
    payload: CollectionItemsReorderRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionItemsOut:
    collection = _get_collection_or_404(db, collection_id)
    _require_owner(collection, current)

    reorder_collection_items(db, collection_id=collection.id, design_ids=payload.design_ids)
    db.commit()
    return _get_items(db, collection, cursor=None, limit=len(payload.design_ids))


@router.get("/{collection_id}/items", response_model=CollectionItemsOut)
def get_items(
    collection_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionItemsOut:
    collection = _get_collection_or_404(db, collection_id)
    _require_viewable(collection, current)
    return _get_items(db, collection, cursor=cursor, limit=max(1, min(limit, 100)))


def _get_items(
    db: Session, collection: Collection, *, cursor: str | None, limit: int
) -> CollectionItemsOut:
    stmt = (
        select(Design)
        .join(CollectionItem, CollectionItem.design_id == Design.id)
        .where(CollectionItem.collection_id == collection.id, Design.deleted_at.is_(None))
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_ITEMS_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        stmt = stmt.where(
            tuple_(CollectionItem.sort_order, Design.id)
            > tuple_(literal(int(decoded.sort_value)), literal(decoded.id))
        )
    stmt = stmt.order_by(CollectionItem.sort_order.asc(), Design.id.asc()).limit(limit + 1)

    rows = list(db.execute(stmt.add_columns(CollectionItem.sort_order)).all())
    has_more = len(rows) > limit
    page = rows[:limit]

    next_cursor = None
    if has_more and page:
        last_design, last_sort_order = page[-1]
        next_cursor = encode_cursor(
            sort=_ITEMS_SORT, sort_value=str(last_sort_order), id_=last_design.id
        )

    designs = [design for design, _sort_order in page]
    return CollectionItemsOut(
        items=summaries_for_designs(db, designs),
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.post("/{collection_id}/items", response_model=CollectionItemsOut, status_code=201)
def add_item(
    collection_id: uuid.UUID,
    payload: CollectionItemAddRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CollectionItemsOut:
    collection = _get_collection_or_404(db, collection_id)
    _require_owner(collection, current)

    design = db.get(Design, payload.design_id)
    if (
        design is None
        or design.deleted_at is not None
        or design.status != DesignStatus.PUBLISHED.value
    ):
        raise AppError("Design not found.", status_code=404)

    add_item_to_collection(db, collection=collection, design_id=design.id)
    db.commit()
    return _get_items(db, collection, cursor=None, limit=100)


@router.delete("/{collection_id}/items/{design_id}", status_code=204)
def remove_item(
    collection_id: uuid.UUID,
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    collection = _get_collection_or_404(db, collection_id)
    _require_owner(collection, current)

    remove_item_from_collection(db, collection=collection, design_id=design_id)
    db.commit()
