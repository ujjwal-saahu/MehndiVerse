import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, require_roles
from app.core.caching import set_public_cache
from app.core.exceptions import AppError
from app.db.models.design import Category
from app.db.session import get_db_session
from app.schemas.design import CategoryCreateRequest, CategoryOut, CategoryUpdateRequest

router = APIRouter(prefix="/categories", tags=["categories"])

_VALID_CATEGORY_TYPES = {"style", "occasion", "body_part", "difficulty", "density", "region"}


def _category_out(category: Category) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        category_type=category.category_type,
        description=category.description,
        parent_category_id=category.parent_category_id,
        sort_order=category.sort_order,
        is_active=category.is_active,
    )


_STAFF_ROLES = {"moderator", "admin", "super_admin"}


@router.get("", response_model=list[CategoryOut])
def list_categories(
    response: Response,
    category_type: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[CategoryOut]:
    if category_type is not None and category_type not in _VALID_CATEGORY_TYPES:
        raise AppError(
            f"category_type must be one of: {', '.join(sorted(_VALID_CATEGORY_TYPES))}",
            status_code=422,
        )
    # Only staff (the admin dashboard's category-management module) may see
    # inactive (soft-deleted) categories — everyone else always gets the
    # active-only taxonomy.
    if include_inactive and current.effective_role not in _STAFF_ROLES:
        raise AppError("Only staff may view inactive categories.", status_code=403)

    stmt = select(Category)
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    if category_type is not None:
        stmt = stmt.where(Category.category_type == category_type)
    if search:
        stmt = stmt.where(func.lower(Category.name).like(f"%{search.lower()}%"))
    stmt = stmt.order_by(Category.category_type, Category.sort_order)

    categories = db.execute(stmt).scalars().all()
    # Taxonomy changes rarely — safe to cache longer than design listings.
    # Only applied to the common (active-only, no search) case — a staff
    # member's filtered admin-dashboard view shouldn't be cached.
    if not include_inactive and search is None:
        set_public_cache(response, max_age_seconds=300)
    return [_category_out(c) for c in categories]


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreateRequest,
    current: AuthenticatedUser = Depends(require_roles("admin", "super_admin")),
    db: Session = Depends(get_db_session),
) -> CategoryOut:
    existing = db.execute(
        select(Category).where(Category.slug == payload.slug)
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("A category with this slug already exists.", status_code=409)

    category = Category(
        name=payload.name,
        slug=payload.slug,
        category_type=payload.category_type,
        description=payload.description,
        parent_category_id=payload.parent_category_id,
        sort_order=payload.sort_order,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return _category_out(category)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles("admin", "super_admin")),
    db: Session = Depends(get_db_session),
) -> CategoryOut:
    category = db.get(Category, category_id)
    if category is None:
        raise AppError("Category not found.", status_code=404)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    db.add(category)
    db.commit()
    db.refresh(category)
    return _category_out(category)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles("admin", "super_admin")),
    db: Session = Depends(get_db_session),
) -> None:
    """Soft-delete only (`is_active = false`) — a category may already be
    attached to published designs via `design_categories`, so it's never
    hard-deleted. Idempotent: deleting an already-inactive category is a
    no-op, not a 404/422, since the end state the caller wants is already
    true."""
    category = db.get(Category, category_id)
    if category is None:
        raise AppError("Category not found.", status_code=404)

    category.is_active = False
    db.add(category)
    db.commit()
