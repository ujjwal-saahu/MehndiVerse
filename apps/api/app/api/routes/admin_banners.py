"""Staff-side promotional banner management — see docs/admin-dashboard.md
#promotional-banners. Brand-new domain this phase (no prior schema, no
public consumption endpoint either — see the model's own docstring for
why); this router is the entire feature for now.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import normalize_pagination, paginate
from app.core.exceptions import AppError
from app.db.models.promotions import PromoBanner
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminPageInfo,
    PromoBannerCreateRequest,
    PromoBannerListOut,
    PromoBannerOut,
    PromoBannerUpdateRequest,
)

router = APIRouter(prefix="/admin/banners", tags=["admin-banners"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")


def _banner_out(banner: PromoBanner) -> PromoBannerOut:
    return PromoBannerOut(
        id=banner.id,
        title=banner.title,
        subtitle=banner.subtitle,
        image_url=banner.image_url,
        link_url=banner.link_url,
        is_active=banner.is_active,
        starts_at=banner.starts_at,
        ends_at=banner.ends_at,
        sort_order=banner.sort_order,
        created_at=banner.created_at,
        updated_at=banner.updated_at,
    )


def _get_banner_or_404(db: Session, banner_id: uuid.UUID) -> PromoBanner:
    banner = db.get(PromoBanner, banner_id)
    if banner is None:
        raise AppError("Banner not found.", status_code=404)
    return banner


@router.get("", response_model=PromoBannerListOut)
def list_banners(
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> PromoBannerListOut:
    page, page_size = normalize_pagination(page, page_size)
    stmt = select(PromoBanner)
    if is_active is not None:
        stmt = stmt.where(PromoBanner.is_active.is_(is_active))
    ordered = stmt.order_by(PromoBanner.sort_order.asc(), PromoBanner.created_at.desc())
    result = paginate(db, ordered, page=page, page_size=page_size)
    return PromoBannerListOut(
        items=[_banner_out(b) for b in result.items],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("", response_model=PromoBannerOut, status_code=201)
def create_banner(
    payload: PromoBannerCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> PromoBannerOut:
    banner = PromoBanner(
        title=payload.title,
        subtitle=payload.subtitle,
        image_url=payload.image_url,
        link_url=payload.link_url,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        sort_order=payload.sort_order,
        created_by=current.user.id,
    )
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return _banner_out(banner)


@router.patch("/{banner_id}", response_model=PromoBannerOut)
def update_banner(
    banner_id: uuid.UUID,
    payload: PromoBannerUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> PromoBannerOut:
    banner = _get_banner_or_404(db, banner_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return _banner_out(banner)


@router.delete("/{banner_id}", status_code=204)
def delete_banner(
    banner_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> None:
    banner = _get_banner_or_404(db, banner_id)
    db.delete(banner)
    db.commit()
