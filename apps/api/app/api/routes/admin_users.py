"""Staff-side user management — see docs/admin-dashboard.md#user-management.

Listing/searching/suspending any user (this phase) sits alongside the
pre-existing role-management endpoint (Phase 9-ish). `_VIEW_ROLES` can browse
and search; only `_EDIT_ROLES` (admin/super_admin) can suspend/reactivate or
change a role — mirroring every other admin_*.py router's RBAC split.
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
from app.core.authz import can_grant_role, get_effective_role
from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import UserRole, UserStatus
from app.db.models.user import Profile, User
from app.db.session import get_db_session
from app.schemas.admin import AdminPageInfo, AdminUserListOut, AdminUserOut, UserSuspendRequest
from app.schemas.auth import RoleUpdateRequest, UserOut
from app.services.audit import record_audit_log

router = APIRouter(prefix="/admin/users", tags=["admin"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")
_VALID_STORED_ROLES = {r.value for r in UserRole}

_SORT_COLUMNS = {
    "created_at": User.created_at,
    "email": User.email,
    "last_login_at": User.last_login_at,
    "status": User.status,
    "role": User.role,
}


def _admin_user_out(user: User, display_name: str | None) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        display_name=display_name,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("", response_model=AdminUserListOut)
def list_users(
    search: str | None = None,
    role: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminUserListOut:
    page, page_size = normalize_pagination(page, page_size)
    sort_key, sort_column = resolve_sort_column(
        sort_by, columns=_SORT_COLUMNS, default_key="created_at"
    )
    direction = resolve_sort_direction(sort_dir)

    stmt = select(User).where(User.deleted_at.is_(None))
    if role is not None:
        if role not in _VALID_STORED_ROLES:
            raise AppError(f"Unknown role: {role}", status_code=422)
        stmt = stmt.where(User.role == role)
    if status_filter is not None:
        if status_filter not in {s.value for s in UserStatus}:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(User.status == status_filter)
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(needle))

    ordered = stmt.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), User.id
    )
    result = paginate(db, ordered, page=page, page_size=page_size)

    names = _display_names(db, [u.id for u in result.items])
    return AdminUserListOut(
        items=[_admin_user_out(u, names.get(u.id)) for u in result.items],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


def _display_names(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(set(user_ids)))
    ).all()
    return {row.user_id: row.display_name for row in rows}


@router.get("/{user_id}", response_model=AdminUserOut)
def get_user(
    user_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminUserOut:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("User not found.", status_code=404)
    names = _display_names(db, [user.id])
    return _admin_user_out(user, names.get(user.id))


@router.post("/{user_id}/suspend", response_model=AdminUserOut)
def suspend_user(
    user_id: uuid.UUID,
    payload: UserSuspendRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminUserOut:
    if user_id == current.user.id:
        raise AuthorizationError("You cannot suspend your own account.")

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("User not found.", status_code=404)
    if user.status == UserStatus.SUSPENDED.value:
        raise AppError("This user is already suspended.", status_code=422)

    before_status = user.status
    user.status = UserStatus.SUSPENDED.value
    db.add(user)
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="user.suspend",
        entity_type="users",
        entity_id=user.id,
        before_state={"status": before_status},
        after_state={"status": user.status, "reason": payload.reason},
    )
    db.commit()
    db.refresh(user)
    names = _display_names(db, [user.id])
    return _admin_user_out(user, names.get(user.id))


@router.post("/{user_id}/reactivate", response_model=AdminUserOut)
def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminUserOut:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("User not found.", status_code=404)
    if user.status != UserStatus.SUSPENDED.value:
        raise AppError("This user is not suspended.", status_code=422)

    before_status = user.status
    user.status = UserStatus.ACTIVE.value
    db.add(user)
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="user.reactivate",
        entity_type="users",
        entity_id=user.id,
        before_state={"status": before_status},
        after_state={"status": user.status},
    )
    db.commit()
    db.refresh(user)
    names = _display_names(db, [user.id])
    return _admin_user_out(user, names.get(user.id))


@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: uuid.UUID,
    payload: RoleUpdateRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles("admin", "super_admin")),
    db: Session = Depends(get_db_session),
) -> UserOut:
    # Privilege-escalation guards — see docs/authentication.md#3. These are
    # deliberately enforced here, not just via require_roles(), because the
    # rule ("can't touch your own role", "admin can't mint another admin")
    # depends on *whose* role is being changed, which require_roles() alone
    # cannot express.
    if user_id == current.user.id:
        raise AuthorizationError("You cannot change your own role.")

    if payload.role not in _VALID_STORED_ROLES:
        raise AppError(f"Unknown role: {payload.role}", status_code=422)

    if not can_grant_role(grantor_role=current.user.role, target_role=payload.role):
        raise AuthorizationError("You are not permitted to grant this role.")

    target_user = db.get(User, user_id)
    if target_user is None:
        raise AppError("User not found.", status_code=404)

    before_role = target_user.role
    target_user.role = payload.role
    db.add(target_user)
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="user.role_change",
        entity_type="users",
        entity_id=target_user.id,
        before_state={"role": before_role},
        after_state={"role": target_user.role},
    )
    db.commit()
    db.refresh(target_user)

    return UserOut(
        id=target_user.id,
        email=target_user.email,
        role=get_effective_role(target_user, db),
        status=target_user.status,
        created_at=target_user.created_at,
    )
