"""Global staff-side audit-log viewer — see docs/admin-dashboard.md#audit-
log-viewer. Every other admin_*.py router that calls `record_audit_log()`
feeds this one view; previously the only way to read `audit_logs` was the
per-artist-profile-scoped endpoint in admin_artist_verification.py. Gated
to admin/super_admin only (not moderator) — audit entries can include
another staff member's privileged actions (role changes, financial
approvals), a step above the moderation-queue-style views moderators
otherwise get read access to.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import normalize_pagination, paginate
from app.db.models.system import AuditLog
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.admin import AdminPageInfo, GlobalAuditLogEntryOut, GlobalAuditLogListOut

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit-log"])

_VIEW_ROLES = ("admin", "super_admin")


@router.get("", response_model=GlobalAuditLogListOut)
def list_audit_logs(
    entity_type: str | None = None,
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> GlobalAuditLogListOut:
    page, page_size = normalize_pagination(page, page_size)
    stmt = select(AuditLog)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    ordered = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    result = paginate(db, ordered, page=page, page_size=page_size)

    actor_ids = [entry.actor_id for entry in result.items if entry.actor_id is not None]
    names: dict[uuid.UUID, str | None] = {}
    if actor_ids:
        rows = db.execute(
            select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(set(actor_ids)))
        ).all()
        names = {row.user_id: row.display_name for row in rows}

    items = [
        GlobalAuditLogEntryOut(
            id=entry.id,
            actor_id=entry.actor_id,
            actor_display_name=names.get(entry.actor_id) if entry.actor_id else None,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            before_state=entry.before_state,
            after_state=entry.after_state,
            created_at=entry.created_at,
        )
        for entry in result.items
    ]
    return GlobalAuditLogListOut(
        items=items,
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )
