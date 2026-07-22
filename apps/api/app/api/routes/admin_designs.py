"""Staff-side design moderation — see docs/admin-dashboard.md#design-
moderation. Distinct from app/api/routes/designs.py's owner/staff-shared
`PATCH`/`archive` endpoints: this router is admin-only, always requires a
reason, and always writes an audit-log entry — the explicit "moderation
action" surface Phase 17 asks for, rather than reusing the general-purpose
edit endpoint that has neither.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import (
    normalize_pagination,
    paginate,
    resolve_sort_column,
    resolve_sort_direction,
)
from app.core.exceptions import AppError
from app.db.enums import DesignStatus
from app.db.models.design import Design
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminDesignListItemOut,
    AdminDesignListOut,
    AdminPageInfo,
    DesignModerateRequest,
)
from app.services.audit import record_audit_log
from app.services.design_summaries import batch_artist_summaries

router = APIRouter(prefix="/admin/designs", tags=["admin-designs"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_ACTION_TO_STATUS = {
    "publish": DesignStatus.PUBLISHED.value,
    "unpublish": DesignStatus.DRAFT.value,
    "archive": DesignStatus.ARCHIVED.value,
    "flag": DesignStatus.FLAGGED.value,
}

_SORT_COLUMNS = {
    "created_at": Design.created_at,
    "title": Design.title,
    "status": Design.status,
    "view_count": Design.view_count,
    "like_count": Design.like_count,
}


def _get_design_or_404(db: Session, design_id: uuid.UUID) -> Design:
    design = db.get(Design, design_id)
    if design is None:
        raise AppError("Design not found.", status_code=404)
    return design


@router.get("", response_model=AdminDesignListOut)
def list_designs(
    search: str | None = None,
    status_filter: str | None = None,
    artist_profile_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminDesignListOut:
    page, page_size = normalize_pagination(page, page_size)
    sort_key, sort_column = resolve_sort_column(
        sort_by, columns=_SORT_COLUMNS, default_key="created_at"
    )
    direction = resolve_sort_direction(sort_dir)

    # Deliberately includes soft-deleted rows (unlike every customer-facing
    # design query) — staff reviewing moderation history need to see a
    # design regardless of its lifecycle state.
    stmt = select(Design)
    if status_filter is not None:
        if status_filter not in {s.value for s in DesignStatus}:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(Design.status == status_filter)
    if artist_profile_id is not None:
        stmt = stmt.where(Design.artist_profile_id == artist_profile_id)
    if search:
        stmt = stmt.where(func.lower(Design.title).like(f"%{search.lower()}%"))

    ordered = stmt.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), Design.id
    )
    result = paginate(db, ordered, page=page, page_size=page_size)

    artist_ids = [d.artist_profile_id for d in result.items if d.artist_profile_id is not None]
    artist_summaries = batch_artist_summaries(db, artist_ids)

    items = [
        AdminDesignListItemOut(
            id=d.id,
            title=d.title,
            status=d.status,
            artist_profile_id=d.artist_profile_id,
            artist_display_name=(
                artist_summaries[d.artist_profile_id].display_name
                if d.artist_profile_id in artist_summaries
                else None
            ),
            is_featured=d.is_featured,
            view_count=d.view_count,
            like_count=d.like_count,
            created_at=d.created_at,
        )
        for d in result.items
    ]
    return AdminDesignListOut(
        items=items,
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("/{design_id}/moderate", response_model=AdminDesignListItemOut)
def moderate_design(
    design_id: uuid.UUID,
    payload: DesignModerateRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminDesignListItemOut:
    design = _get_design_or_404(db, design_id)
    to_status = _ACTION_TO_STATUS.get(payload.action)
    if to_status is None:
        raise AppError(
            f"Unknown moderation action '{payload.action}'. Choose one of: "
            f"{', '.join(sorted(_ACTION_TO_STATUS))}.",
            status_code=422,
        )
    if design.status == to_status:
        raise AppError(f"This design is already '{to_status}'.", status_code=422)

    before_status = design.status
    design.status = to_status
    db.add(design)
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action=f"design.moderate.{payload.action}",
        entity_type="designs",
        entity_id=design.id,
        before_state={"status": before_status},
        after_state={"status": to_status, "reason": payload.reason},
    )
    db.commit()
    db.refresh(design)

    artist_summaries = (
        batch_artist_summaries(db, [design.artist_profile_id])
        if design.artist_profile_id is not None
        else {}
    )
    return AdminDesignListItemOut(
        id=design.id,
        title=design.title,
        status=design.status,
        artist_profile_id=design.artist_profile_id,
        artist_display_name=(
            artist_summaries[design.artist_profile_id].display_name
            if design.artist_profile_id in artist_summaries
            else None
        ),
        is_featured=design.is_featured,
        view_count=design.view_count,
        like_count=design.like_count,
        created_at=design.created_at,
    )
