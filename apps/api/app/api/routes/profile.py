import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError, AuthorizationError
from app.core.images import ALLOWED_CONTENT_TYPES, InvalidImageError, process_avatar_upload
from app.db.models.user import Profile, User, UserBlock, UserPreference
from app.db.session import get_db_session
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError
from app.schemas.profile import (
    AvatarUploadResponse,
    BlockedUserOut,
    BlockUserRequest,
    ProfileOut,
    ProfileUpdateRequest,
    UserPreferencesOut,
    UserPreferencesUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["profile"])


def _get_or_create_profile(db: Session, user: User) -> Profile:
    # Registration always creates a Profile row (see app/api/routes/auth.py),
    # but a lazily-provisioned account (see get_current_user in app/api/
    # deps.py) does not — this keeps every authenticated user resolvable to a
    # usable profile regardless of how their `users` row came to exist.
    profile = db.execute(select(Profile).where(Profile.user_id == user.id)).scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id, display_name=user.email.split("@")[0])
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _get_or_create_preferences(db: Session, user: User) -> UserPreference:
    prefs = db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    ).scalar_one_or_none()
    if prefs is None:
        prefs = UserPreference(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def _profile_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        user_id=profile.user_id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        city=profile.city,
        country=profile.country,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _preferences_out(prefs: UserPreference) -> UserPreferencesOut:
    return UserPreferencesOut(
        email_notifications=prefs.email_notifications,
        push_notifications=prefs.push_notifications,
        sms_notifications=prefs.sms_notifications,
        marketing_opt_in=prefs.marketing_opt_in,
        profile_visibility=prefs.profile_visibility,
        show_location=prefs.show_location,
        allow_messages_from_strangers=prefs.allow_messages_from_strangers,
        analytics_consent=prefs.analytics_consent,
    )


@router.get("/me/profile", response_model=ProfileOut)
def get_my_profile(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProfileOut:
    return _profile_out(_get_or_create_profile(db, current.user))


@router.patch("/me/profile", response_model=ProfileOut)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProfileOut:
    profile = _get_or_create_profile(db, current.user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_out(profile)


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_my_avatar(
    file: UploadFile,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AvatarUploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise AppError("Unsupported image type. Use JPEG, PNG, or WEBP.", status_code=422)

    raw = await file.read()
    try:
        processed = process_avatar_upload(raw)
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc

    path = f"{current.user.id}/avatar.{processed.extension}"
    try:
        avatar_url = supabase_storage.upload_object(
            bucket="avatars", path=path, data=processed.data, content_type=processed.content_type
        )
    except SupabaseStorageError as exc:
        raise AppError("Failed to upload image. Please try again.", status_code=502) from exc

    profile = _get_or_create_profile(db, current.user)
    profile.avatar_url = avatar_url
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return AvatarUploadResponse(avatar_url=avatar_url)


@router.get("/me/preferences", response_model=UserPreferencesOut)
def get_my_preferences(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserPreferencesOut:
    return _preferences_out(_get_or_create_preferences(db, current.user))


@router.patch("/me/preferences", response_model=UserPreferencesOut)
def update_my_preferences(
    payload: UserPreferencesUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserPreferencesOut:
    prefs = _get_or_create_preferences(db, current.user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return _preferences_out(prefs)


@router.get("/{user_id}/profile", response_model=ProfileOut)
def get_public_profile(
    user_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProfileOut:
    """Read-only view of another user's profile. A private profile is
    invisible to everyone except its owner and staff — returned as 404
    rather than 403 so a stranger can't use the response code to confirm a
    user id exists. Editing is never reachable this way: every write
    endpoint above operates on `current.user`, never on a path parameter, so
    there is no route through which one user can edit another's profile."""
    target_user = db.get(User, user_id)
    if target_user is None:
        raise AppError("Profile not found.", status_code=404)

    profile = _get_or_create_profile(db, target_user)
    is_owner = target_user.id == current.user.id
    is_staff = current.effective_role in {"moderator", "admin", "super_admin"}

    if not is_owner and not is_staff:
        prefs = _get_or_create_preferences(db, target_user)
        if prefs.profile_visibility == "private":
            raise AppError("Profile not found.", status_code=404)
        if not prefs.show_location:
            profile.city = None
            profile.country = None

    return _profile_out(profile)


@router.get("/me/blocks", response_model=list[BlockedUserOut])
def list_my_blocks(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[BlockedUserOut]:
    blocks = (
        db.execute(select(UserBlock).where(UserBlock.blocker_id == current.user.id)).scalars().all()
    )
    result = []
    for block in blocks:
        profile = db.execute(
            select(Profile).where(Profile.user_id == block.blocked_id)
        ).scalar_one_or_none()
        result.append(
            BlockedUserOut(
                user_id=block.blocked_id,
                display_name=profile.display_name if profile else None,
                blocked_at=block.created_at,
            )
        )
    return result


@router.post("/me/blocks", response_model=BlockedUserOut, status_code=201)
def block_user(
    payload: BlockUserRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BlockedUserOut:
    if payload.user_id == current.user.id:
        raise AuthorizationError("You cannot block yourself.")

    target_user = db.get(User, payload.user_id)
    if target_user is None:
        raise AppError("User not found.", status_code=404)

    existing = db.execute(
        select(UserBlock).where(
            UserBlock.blocker_id == current.user.id, UserBlock.blocked_id == payload.user_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("You have already blocked this user.", status_code=409)

    block = UserBlock(blocker_id=current.user.id, blocked_id=payload.user_id)
    db.add(block)
    db.commit()
    db.refresh(block)

    profile = db.execute(
        select(Profile).where(Profile.user_id == payload.user_id)
    ).scalar_one_or_none()
    return BlockedUserOut(
        user_id=block.blocked_id,
        display_name=profile.display_name if profile else None,
        blocked_at=block.created_at,
    )


@router.delete("/me/blocks/{user_id}", status_code=204)
def unblock_user(
    user_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    block = db.execute(
        select(UserBlock).where(
            UserBlock.blocker_id == current.user.id, UserBlock.blocked_id == user_id
        )
    ).scalar_one_or_none()
    if block is None:
        raise AppError("Block not found.", status_code=404)

    db.delete(block)
    db.commit()
