"""Super-admin-only system settings — see docs/admin-dashboard.md#system-
settings. `SystemSetting` (app/db/models/system.py) existed since Phase 2
as pure unused schema; this is the first read/write surface for it. Every
mutation is audit-logged — changing runtime configuration is exactly the
kind of privileged change Phase 17 requires a trail for.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError
from app.db.models.system import SystemSetting
from app.db.session import get_db_session
from app.schemas.admin import SystemSettingListOut, SystemSettingOut, SystemSettingUpsertRequest
from app.services.audit import record_audit_log

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

# System settings are the one module this phase's requirements explicitly
# call "super-admin-only" by name — see docs/admin-dashboard.md#super-
# admin-only-modules. Not even a view-only tier for admin/moderator.
_ROLES = ("super_admin",)


def _setting_out(setting: SystemSetting) -> SystemSettingOut:
    return SystemSettingOut(
        id=setting.id,
        key=setting.key,
        value=setting.value,
        description=setting.description,
        is_public=setting.is_public,
        updated_by=setting.updated_by,
        updated_at=setting.updated_at,
    )


@router.get("", response_model=SystemSettingListOut)
def list_settings(
    current: AuthenticatedUser = Depends(require_roles(*_ROLES)),
    db: Session = Depends(get_db_session),
) -> SystemSettingListOut:
    settings = db.execute(select(SystemSetting).order_by(SystemSetting.key.asc())).scalars().all()
    return SystemSettingListOut(items=[_setting_out(s) for s in settings])


@router.put("/{key}", response_model=SystemSettingOut)
def upsert_setting(
    key: str,
    payload: SystemSettingUpsertRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_ROLES)),
    db: Session = Depends(get_db_session),
) -> SystemSettingOut:
    if not key or len(key) > 100:
        raise AppError("A setting key must be 1-100 characters.", status_code=422)

    setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    before_state = {"value": setting.value} if setting is not None else None

    if setting is None:
        setting = SystemSetting(key=key, value=payload.value)
    setting.value = payload.value
    setting.description = payload.description
    setting.is_public = payload.is_public
    setting.updated_by = current.user.id
    db.add(setting)
    db.flush()

    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="system_setting.upsert",
        entity_type="system_settings",
        entity_id=setting.id,
        before_state=before_state,
        after_state={"key": key, "value": payload.value},
    )
    db.commit()
    db.refresh(setting)
    return _setting_out(setting)
