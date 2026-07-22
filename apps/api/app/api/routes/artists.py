"""Public artist directory and profile — see docs/artist-directory.md.

Mirrors app/api/routes/designs.py's visibility convention: a stranger gets
404 (not 403) for a non-public profile, so its existence isn't leaked; the
owner or staff can always see their own/any profile regardless of
verification status.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.caching import set_public_cache
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import AnalyticsEventType
from app.db.models.artist import ArtistProfile, ArtistService
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.artist_directory import (
    ArtistDirectoryItemOut,
    ArtistDirectoryListOut,
    ArtistPublicProfileOut,
)
from app.schemas.design import PageInfo
from app.schemas.scheduling import AvailableSlotOut, AvailableSlotsOut
from app.services.analytics.events import record_event
from app.services.artist_directory import (
    PUBLIC_DIRECTORY_STATUSES,
    artist_public_profile_out,
    follow_artist,
    is_publicly_visible,
    unfollow_artist,
)
from app.services.scheduling import compute_available_slots

router = APIRouter(prefix="/artists", tags=["artists"])

_VIEW_STAFF_ROLES = {"moderator", "admin", "super_admin"}
_DIRECTORY_SORT = "artist_directory"


def _is_owner(profile: ArtistProfile, current: AuthenticatedUser) -> bool:
    return profile.user_id == current.user.id


def _get_visible_profile_or_404(
    db: Session, artist_profile_id: uuid.UUID, current: AuthenticatedUser
) -> ArtistProfile:
    profile = db.get(ArtistProfile, artist_profile_id)
    if profile is None or profile.deleted_at is not None:
        raise AppError("Artist not found.", status_code=404)
    can_view_hidden = current.effective_role in _VIEW_STAFF_ROLES or _is_owner(profile, current)
    if not is_publicly_visible(profile) and not can_view_hidden:
        raise AppError("Artist not found.", status_code=404)
    return profile


def _directory_item_out(
    profile: ArtistProfile, contact_profile: Profile | None
) -> ArtistDirectoryItemOut:
    return ArtistDirectoryItemOut(
        id=profile.id,
        display_name=(
            profile.professional_name
            or profile.business_name
            or (contact_profile.display_name if contact_profile else None)
            or "Independent Artist"
        ),
        headline=profile.headline,
        avatar_url=profile.profile_image_url
        or (contact_profile.avatar_url if contact_profile else None),
        city=profile.city,
        country=profile.country,
        years_experience=profile.years_experience,
        is_verified=profile.verification_status == "approved",
        rating_average=float(profile.rating_average),
        rating_count=profile.rating_count,
        is_accepting_bookings=profile.is_accepting_bookings,
    )


@router.get("", response_model=ArtistDirectoryListOut)
def list_artists(
    response: Response,
    city: str | None = None,
    country: str | None = None,
    service: str | None = None,
    min_rating: float | None = None,
    verified_only: bool = True,
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistDirectoryListOut:
    limit = max(1, min(limit, 100))
    if min_rating is not None and not (0 <= min_rating <= 5):
        raise AppError("min_rating must be between 0 and 5.", status_code=422)

    statuses = {"approved"} if verified_only else PUBLIC_DIRECTORY_STATUSES
    stmt = select(ArtistProfile).where(
        ArtistProfile.verification_status.in_(statuses), ArtistProfile.deleted_at.is_(None)
    )
    if city:
        stmt = stmt.where(ArtistProfile.city.ilike(f"%{city}%"))
    if country:
        stmt = stmt.where(ArtistProfile.country == country.strip().upper())
    if min_rating is not None:
        stmt = stmt.where(ArtistProfile.rating_average >= min_rating)
    if service:
        # Foundation-level substring match against the artist's own active
        # services — not a full-text/category search (see
        # docs/artist-directory.md#service-filter-is-a-foundation).
        stmt = stmt.join(ArtistService, ArtistService.artist_profile_id == ArtistProfile.id).where(
            ArtistService.is_active.is_(True),
            ArtistService.deleted_at.is_(None),
            ArtistService.name.ilike(f"%{service}%"),
        )

    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_DIRECTORY_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_rating = float(decoded.sort_value)
        stmt = stmt.where(
            tuple_(ArtistProfile.rating_average, ArtistProfile.id)
            < tuple_(literal(cursor_rating), literal(decoded.id))
        )

    stmt = (
        stmt.distinct()
        .order_by(ArtistProfile.rating_average.desc(), ArtistProfile.id.desc())
        .limit(limit + 1)
    )

    profiles = list(db.execute(stmt).scalars().all())
    has_more = len(profiles) > limit
    page = profiles[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_DIRECTORY_SORT, sort_value=str(last.rating_average), id_=last.id
        )

    contact_profiles_by_user: dict[uuid.UUID, Profile] = {}
    if page:
        rows = db.execute(
            select(Profile).where(Profile.user_id.in_([p.user_id for p in page]))
        ).scalars()
        contact_profiles_by_user = {row.user_id: row for row in rows}

    items = [_directory_item_out(p, contact_profiles_by_user.get(p.user_id)) for p in page]

    set_public_cache(response, max_age_seconds=30)
    return ArtistDirectoryListOut(
        items=items, page_info=PageInfo(next_cursor=next_cursor, has_more=has_more)
    )


@router.get("/{artist_profile_id}", response_model=ArtistPublicProfileOut)
def get_artist(
    artist_profile_id: uuid.UUID,
    response: Response,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistPublicProfileOut:
    profile = _get_visible_profile_or_404(db, artist_profile_id, current)
    if is_publicly_visible(profile):
        set_public_cache(response, max_age_seconds=30)
    result = artist_public_profile_out(db, profile, viewer_user_id=current.user.id)
    record_event(
        db,
        event_type=AnalyticsEventType.ARTIST_VIEWED.value,
        user_id=current.user.id,
        entity_type="artist_profile",
        entity_id=profile.id,
    )
    db.commit()
    return result


@router.get("/{artist_profile_id}/availability/slots", response_model=AvailableSlotsOut)
def get_artist_available_slots(
    artist_profile_id: uuid.UUID,
    service_id: uuid.UUID,
    start_date: date,
    end_date: date,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AvailableSlotsOut:
    """Read-only slot calculation — see docs/artist-scheduling.md. Does not
    create a `Booking`; booking creation is a later phase."""
    profile = _get_visible_profile_or_404(db, artist_profile_id, current)
    service = db.get(ArtistService, service_id)
    if (
        service is None
        or service.artist_profile_id != profile.id
        or service.deleted_at is not None
        or not service.is_active
    ):
        raise AppError("Service not found.", status_code=404)

    slots = compute_available_slots(db, profile, service, start_date=start_date, end_date=end_date)
    return AvailableSlotsOut(
        artist_profile_id=profile.id,
        service_id=service.id,
        artist_timezone=profile.timezone,
        slots=[AvailableSlotOut(start=s.start_utc, end=s.end_utc) for s in slots],
    )


@router.post("/{artist_profile_id}/follow", status_code=204)
def follow(
    artist_profile_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    profile = _get_visible_profile_or_404(db, artist_profile_id, current)
    if profile.user_id == current.user.id:
        raise AppError("You cannot follow yourself.", status_code=422)
    follow_artist(db, follower_user_id=current.user.id, artist_profile=profile)
    db.commit()


@router.delete("/{artist_profile_id}/follow", status_code=204)
def unfollow(
    artist_profile_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    unfollow_artist(db, follower_user_id=current.user.id, artist_profile_id=artist_profile_id)
    db.commit()
