"""Staff-side featured-collection curation — see docs/admin-dashboard.md
#featured-collections. Brand-new domain this phase — a staff-curated group
of designs for homepage merchandising, distinct from the pre-existing
user-owned `collections` (app/api/routes/collections.py).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import normalize_pagination, paginate
from app.core.exceptions import AppError
from app.db.models.design import Design
from app.db.models.promotions import FeaturedCollection, FeaturedCollectionItem
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminPageInfo,
    FeaturedCollectionAddItemRequest,
    FeaturedCollectionCreateRequest,
    FeaturedCollectionItemOut,
    FeaturedCollectionListOut,
    FeaturedCollectionOut,
    FeaturedCollectionUpdateRequest,
)

router = APIRouter(prefix="/admin/featured-collections", tags=["admin-featured-collections"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")


def _collection_out(collection: FeaturedCollection) -> FeaturedCollectionOut:
    return FeaturedCollectionOut(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        cover_image_url=collection.cover_image_url,
        is_active=collection.is_active,
        sort_order=collection.sort_order,
        items=[
            FeaturedCollectionItemOut(id=i.id, design_id=i.design_id, sort_order=i.sort_order)
            for i in collection.items
        ],
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def _get_collection_or_404(db: Session, collection_id: uuid.UUID) -> FeaturedCollection:
    collection = db.execute(
        select(FeaturedCollection)
        .where(FeaturedCollection.id == collection_id)
        .options(selectinload(FeaturedCollection.items))
    ).scalar_one_or_none()
    if collection is None:
        raise AppError("Featured collection not found.", status_code=404)
    return collection


@router.get("", response_model=FeaturedCollectionListOut)
def list_featured_collections(
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> FeaturedCollectionListOut:
    page, page_size = normalize_pagination(page, page_size)
    stmt = select(FeaturedCollection).options(selectinload(FeaturedCollection.items))
    if is_active is not None:
        stmt = stmt.where(FeaturedCollection.is_active.is_(is_active))
    ordered = stmt.order_by(
        FeaturedCollection.sort_order.asc(), FeaturedCollection.created_at.desc()
    )
    result = paginate(db, ordered, page=page, page_size=page_size)
    return FeaturedCollectionListOut(
        items=[_collection_out(c) for c in result.items],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("", response_model=FeaturedCollectionOut, status_code=201)
def create_featured_collection(
    payload: FeaturedCollectionCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> FeaturedCollectionOut:
    collection = FeaturedCollection(
        title=payload.title,
        description=payload.description,
        cover_image_url=payload.cover_image_url,
        sort_order=payload.sort_order,
        created_by=current.user.id,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return _collection_out(collection)


@router.patch("/{collection_id}", response_model=FeaturedCollectionOut)
def update_featured_collection(
    collection_id: uuid.UUID,
    payload: FeaturedCollectionUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> FeaturedCollectionOut:
    collection = _get_collection_or_404(db, collection_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(collection, field, value)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return _collection_out(collection)


@router.delete("/{collection_id}", status_code=204)
def delete_featured_collection(
    collection_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> None:
    collection = _get_collection_or_404(db, collection_id)
    db.delete(collection)
    db.commit()


@router.post("/{collection_id}/items", response_model=FeaturedCollectionOut, status_code=201)
def add_featured_collection_item(
    collection_id: uuid.UUID,
    payload: FeaturedCollectionAddItemRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> FeaturedCollectionOut:
    _get_collection_or_404(db, collection_id)
    design = db.get(Design, payload.design_id)
    if design is None:
        raise AppError("Design not found.", status_code=404)

    existing = db.execute(
        select(FeaturedCollectionItem.id).where(
            FeaturedCollectionItem.featured_collection_id == collection_id,
            FeaturedCollectionItem.design_id == payload.design_id,
        )
    ).first()
    if existing is not None:
        raise AppError("This design is already in the collection.", status_code=409)

    db.add(
        FeaturedCollectionItem(
            featured_collection_id=collection_id,
            design_id=payload.design_id,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    return _collection_out(_get_collection_or_404(db, collection_id))


@router.delete("/{collection_id}/items/{item_id}", response_model=FeaturedCollectionOut)
def remove_featured_collection_item(
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> FeaturedCollectionOut:
    _get_collection_or_404(db, collection_id)
    item = db.get(FeaturedCollectionItem, item_id)
    if item is None or item.featured_collection_id != collection_id:
        raise AppError("Item not found in this collection.", status_code=404)
    db.delete(item)
    db.commit()
    return _collection_out(_get_collection_or_404(db, collection_id))
