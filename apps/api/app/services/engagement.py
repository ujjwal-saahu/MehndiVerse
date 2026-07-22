"""Likes, saves, and collection membership — see
docs/engagement-and-collections.md.

Likes and saves both follow the same "insert, then treat a unique-constraint
conflict as already-done" pattern rather than a SELECT-then-INSERT check: the
DB constraint is the single source of truth for "does this already exist", so
two concurrent identical requests can never double-insert or double-count —
whichever one loses the race just observes the conflict and returns the same
result as the winner, rather than erroring. Each attempt is wrapped in a
SAVEPOINT (`db.begin_nested()`) so a losing attempt's failed INSERT doesn't
poison the rest of the request's transaction.
"""

import uuid
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import AnalyticsEventType
from app.db.models.design import Design
from app.db.models.engagement import Collection, CollectionItem, Like
from app.services.analytics.events import record_event

DEFAULT_COLLECTION_NAME = "Saved Designs"


def is_liked_by(db: Session, *, user_id: uuid.UUID, design_id: uuid.UUID) -> bool:
    return (
        db.execute(
            select(Like.id).where(Like.user_id == user_id, Like.design_id == design_id)
        ).first()
        is not None
    )


def like_design(db: Session, *, user_id: uuid.UUID, design_id: uuid.UUID) -> None:
    try:
        with db.begin_nested():
            db.add(Like(user_id=user_id, design_id=design_id))
            db.flush()
    except IntegrityError:
        return  # already liked — idempotent no-op
    db.execute(
        update(Design).where(Design.id == design_id).values(like_count=Design.like_count + 1)
    )
    record_event(
        db,
        event_type=AnalyticsEventType.DESIGN_LIKED.value,
        user_id=user_id,
        entity_type="design",
        entity_id=design_id,
    )


def unlike_design(db: Session, *, user_id: uuid.UUID, design_id: uuid.UUID) -> None:
    result = cast(
        CursorResult[Any],
        db.execute(delete(Like).where(Like.user_id == user_id, Like.design_id == design_id)),
    )
    if result.rowcount:
        db.execute(
            update(Design)
            .where(Design.id == design_id, Design.like_count > 0)
            .values(like_count=Design.like_count - 1)
        )


def get_default_collection(db: Session, *, user_id: uuid.UUID) -> Collection | None:
    return db.execute(
        select(Collection).where(
            Collection.user_id == user_id,
            Collection.is_default.is_(True),
            Collection.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def get_or_create_default_collection(db: Session, *, user_id: uuid.UUID) -> Collection:
    existing = get_default_collection(db, user_id=user_id)
    if existing is not None:
        return existing
    try:
        with db.begin_nested():
            collection = Collection(
                user_id=user_id,
                name=DEFAULT_COLLECTION_NAME,
                is_default=True,
                is_private=True,
            )
            db.add(collection)
            db.flush()
            return collection
    except IntegrityError:
        # Lost a race to create it (concurrent first-save), or a collection
        # already has this exact name without being the default one.
        winner = get_default_collection(db, user_id=user_id)
        if winner is not None:
            return winner
        raise AppError(
            f'Could not create your "{DEFAULT_COLLECTION_NAME}" collection because a '
            "collection with that name already exists.",
            status_code=409,
        ) from None


def is_saved_by(db: Session, *, user_id: uuid.UUID, design_id: uuid.UUID) -> bool:
    collection = get_default_collection(db, user_id=user_id)
    if collection is None:
        return False
    return (
        db.execute(
            select(CollectionItem.id).where(
                CollectionItem.collection_id == collection.id,
                CollectionItem.design_id == design_id,
            )
        ).first()
        is not None
    )


def add_item_to_collection(db: Session, *, collection: Collection, design_id: uuid.UUID) -> bool:
    """Returns True if the item was newly added, False if it was already there."""
    next_sort_order = db.execute(
        select(func.coalesce(func.max(CollectionItem.sort_order), -1) + 1).where(
            CollectionItem.collection_id == collection.id
        )
    ).scalar_one()
    try:
        with db.begin_nested():
            db.add(
                CollectionItem(
                    collection_id=collection.id,
                    design_id=design_id,
                    sort_order=next_sort_order,
                )
            )
            db.flush()
    except IntegrityError:
        return False
    if collection.is_default:
        db.execute(
            update(Design).where(Design.id == design_id).values(save_count=Design.save_count + 1)
        )
        record_event(
            db,
            event_type=AnalyticsEventType.DESIGN_SAVED.value,
            user_id=collection.user_id,
            entity_type="design",
            entity_id=design_id,
        )
    return True


def remove_item_from_collection(
    db: Session, *, collection: Collection, design_id: uuid.UUID
) -> bool:
    """Returns True if an item was actually removed."""
    result = cast(
        CursorResult[Any],
        db.execute(
            delete(CollectionItem).where(
                CollectionItem.collection_id == collection.id,
                CollectionItem.design_id == design_id,
            )
        ),
    )
    removed = bool(result.rowcount)
    if removed and collection.is_default:
        db.execute(
            update(Design)
            .where(Design.id == design_id, Design.save_count > 0)
            .values(save_count=Design.save_count - 1)
        )
    return removed


def reorder_collection_items(
    db: Session, *, collection_id: uuid.UUID, design_ids: list[uuid.UUID]
) -> None:
    """`design_ids` must be exactly the collection's current design ids, in
    the desired new order — a partial reorder would leave the un-mentioned
    items' positions ambiguous, so it's rejected rather than guessed at."""
    current_ids = set(
        db.execute(
            select(CollectionItem.design_id).where(CollectionItem.collection_id == collection_id)
        )
        .scalars()
        .all()
    )
    if len(design_ids) != len(set(design_ids)) or set(design_ids) != current_ids:
        raise AppError(
            "The reorder list must contain exactly the designs currently in this "
            "collection, each exactly once.",
            status_code=422,
        )
    for index, design_id in enumerate(design_ids):
        db.execute(
            update(CollectionItem)
            .where(
                CollectionItem.collection_id == collection_id,
                CollectionItem.design_id == design_id,
            )
            .values(sort_order=index)
        )


def resolve_cover_urls(
    db: Session, collections: list[Collection]
) -> dict[uuid.UUID, uuid.UUID | None]:
    """Batched cover-design resolution for a list of collections — one query
    for however many collections need a fallback lookup, not one per
    collection. Prefers each collection's explicit `cover_design_id` (if that
    design still exists); falls back to its most-recently-added item."""
    result: dict[uuid.UUID, uuid.UUID | None] = {}
    needs_fallback: list[uuid.UUID] = []

    explicit_ids = [c.cover_design_id for c in collections if c.cover_design_id is not None]
    existing_explicit: set[uuid.UUID] = set()
    if explicit_ids:
        existing_explicit = set(
            db.execute(select(Design.id).where(Design.id.in_(explicit_ids))).scalars().all()
        )

    for collection in collections:
        if (
            collection.cover_design_id is not None
            and collection.cover_design_id in existing_explicit
        ):
            result[collection.id] = collection.cover_design_id
        else:
            needs_fallback.append(collection.id)

    if needs_fallback:
        rows = db.execute(
            select(CollectionItem.collection_id, CollectionItem.design_id)
            .where(CollectionItem.collection_id.in_(needs_fallback))
            .order_by(CollectionItem.collection_id, CollectionItem.added_at.desc())
        ).all()
        latest_by_collection: dict[uuid.UUID, uuid.UUID] = {}
        for collection_id, design_id in rows:
            latest_by_collection.setdefault(collection_id, design_id)
        for collection_id in needs_fallback:
            result[collection_id] = latest_by_collection.get(collection_id)

    return result
