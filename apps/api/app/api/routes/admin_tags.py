"""Staff-side tag management — see docs/admin-dashboard.md#tag-management.

Tags (`app/db/models/design.py::Tag`) previously had no CRUD surface at
all — they were only ever created implicitly by `tag_names` on design
create/update (see app/api/routes/designs.py). This is the first place an
admin can rename or remove one directly.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import normalize_pagination, paginate
from app.core.exceptions import AppError
from app.db.models.design import Tag
from app.db.session import get_db_session
from app.schemas.admin import AdminPageInfo, TagCreateRequest, TagListOut, TagOut, TagUpdateRequest

router = APIRouter(prefix="/admin/tags", tags=["admin-tags"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")


def _tag_out(tag: Tag) -> TagOut:
    return TagOut(id=tag.id, name=tag.name, slug=tag.slug)


def _get_tag_or_404(db: Session, tag_id: uuid.UUID) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise AppError("Tag not found.", status_code=404)
    return tag


def _assert_unique(
    db: Session, *, name: str, slug: str, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(Tag.id).where((Tag.name == name) | (Tag.slug == slug))
    if exclude_id is not None:
        stmt = stmt.where(Tag.id != exclude_id)
    if db.execute(stmt).first() is not None:
        raise AppError("A tag with this name or slug already exists.", status_code=409)


@router.get("", response_model=TagListOut)
def list_tags(
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> TagListOut:
    page, page_size = normalize_pagination(page, page_size)
    stmt = select(Tag)
    if search:
        stmt = stmt.where(func.lower(Tag.name).like(f"%{search.lower()}%"))
    ordered = stmt.order_by(Tag.name.asc())
    result = paginate(db, ordered, page=page, page_size=page_size)
    return TagListOut(
        items=[_tag_out(t) for t in result.items],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("", response_model=TagOut, status_code=201)
def create_tag(
    payload: TagCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> TagOut:
    _assert_unique(db, name=payload.name, slug=payload.slug)
    tag = Tag(name=payload.name, slug=payload.slug)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_out(tag)


@router.patch("/{tag_id}", response_model=TagOut)
def update_tag(
    tag_id: uuid.UUID,
    payload: TagUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> TagOut:
    tag = _get_tag_or_404(db, tag_id)
    _assert_unique(
        db, name=payload.name or tag.name, slug=payload.slug or tag.slug, exclude_id=tag.id
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_out(tag)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    tag_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> None:
    """Hard delete — a tag is a plain taxonomy label (unlike a category, it
    carries no independent meaning worth preserving), and `design_tags` rows
    referencing it cascade automatically."""
    tag = _get_tag_or_404(db, tag_id)
    db.delete(tag)
    db.commit()
