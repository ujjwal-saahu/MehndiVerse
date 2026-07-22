"""Public artist directory/profile, follow/unfollow, and portfolio analytics
— see docs/artist-directory.md.

Follow/unfollow mirrors app/services/engagement.py's "insert, then treat a
unique-constraint conflict as already-done" pattern rather than a
SELECT-then-INSERT check — see that module's docstring for why.
"""

import uuid
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import ArtistVerificationStatus, DesignStatus
from app.db.models.artist import ArtistAvailability, ArtistProfile, ArtistService
from app.db.models.design import Design
from app.db.models.engagement import Follow
from app.db.models.user import Profile
from app.schemas.artist_directory import (
    ArtistAvailabilitySlotOut,
    ArtistPublicProfileOut,
    ArtistServiceOut,
)
from app.services.blocking import is_blocked_either_direction
from app.services.design_summaries import summaries_for_designs

# Draft/rejected/suspended/more-information-required artists have no public
# presence at all — they haven't (or no longer) passed even the "submitted"
# bar. `verified_only=True` (the default) further narrows this to APPROVED
# only. See docs/artist-directory.md#directory-visibility.
PUBLIC_DIRECTORY_STATUSES = frozenset(
    {
        ArtistVerificationStatus.SUBMITTED.value,
        ArtistVerificationStatus.UNDER_REVIEW.value,
        ArtistVerificationStatus.APPROVED.value,
    }
)

PORTFOLIO_PREVIEW_LIMIT = 12
AVAILABILITY_PREVIEW_LIMIT = 14  # up to two slots/day across a week


def is_publicly_visible(profile: ArtistProfile) -> bool:
    return profile.verification_status in PUBLIC_DIRECTORY_STATUSES


def is_following(db: Session, *, user_id: uuid.UUID, artist_profile_id: uuid.UUID) -> bool:
    return (
        db.execute(
            select(Follow.id).where(
                Follow.follower_user_id == user_id, Follow.artist_profile_id == artist_profile_id
            )
        ).first()
        is not None
    )


def follow_artist(
    db: Session, *, follower_user_id: uuid.UUID, artist_profile: ArtistProfile
) -> None:
    # See docs/community-and-trust.md#6-blocked-users-cannot-directly-interact
    # — following is a direct interaction just like commenting or messaging.
    if is_blocked_either_direction(db, follower_user_id, artist_profile.user_id):
        raise AppError(
            "You can't follow this artist — one of you has blocked the other.", status_code=403
        )
    try:
        with db.begin_nested():
            db.add(Follow(follower_user_id=follower_user_id, artist_profile_id=artist_profile.id))
            db.flush()
    except IntegrityError:
        return  # already following — idempotent no-op
    db.execute(
        update(ArtistProfile)
        .where(ArtistProfile.id == artist_profile.id)
        .values(follower_count=ArtistProfile.follower_count + 1)
    )


def unfollow_artist(
    db: Session, *, follower_user_id: uuid.UUID, artist_profile_id: uuid.UUID
) -> None:
    result = cast(
        CursorResult[Any],
        db.execute(
            delete(Follow).where(
                Follow.follower_user_id == follower_user_id,
                Follow.artist_profile_id == artist_profile_id,
            )
        ),
    )
    if result.rowcount:
        db.execute(
            update(ArtistProfile)
            .where(ArtistProfile.id == artist_profile_id, ArtistProfile.follower_count > 0)
            .values(follower_count=ArtistProfile.follower_count - 1)
        )


def _display_name(artist_profile: ArtistProfile, profile: Profile | None) -> str:
    return (
        artist_profile.professional_name
        or artist_profile.business_name
        or (profile.display_name if profile else None)
        or "Independent Artist"
    )


def service_out(service: ArtistService) -> ArtistServiceOut:
    return ArtistServiceOut(
        id=service.id,
        name=service.name,
        description=service.description,
        pricing_type=service.pricing_type,
        price_amount=service.price_amount,
        price_min=service.price_min,
        price_max=service.price_max,
        currency=service.currency,
        duration_minutes=service.duration_minutes,
        customer_capacity=service.customer_capacity,
        deposit_required=service.deposit_required,
        deposit_amount=service.deposit_amount,
        travel_charge_amount=service.travel_charge_amount,
        cancellation_policy=service.cancellation_policy,
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )


def artist_public_profile_out(
    db: Session, artist_profile: ArtistProfile, *, viewer_user_id: uuid.UUID
) -> ArtistPublicProfileOut:
    profile = db.execute(
        select(Profile).where(Profile.user_id == artist_profile.user_id)
    ).scalar_one_or_none()

    services = (
        db.execute(
            select(ArtistService)
            .where(
                ArtistService.artist_profile_id == artist_profile.id,
                ArtistService.is_active.is_(True),
                ArtistService.deleted_at.is_(None),
            )
            .order_by(ArtistService.created_at)
        )
        .scalars()
        .all()
    )

    availability = (
        db.execute(
            select(ArtistAvailability)
            .where(
                ArtistAvailability.artist_profile_id == artist_profile.id,
                ArtistAvailability.is_active.is_(True),
            )
            .order_by(ArtistAvailability.day_of_week, ArtistAvailability.start_time)
            .limit(AVAILABILITY_PREVIEW_LIMIT)
        )
        .scalars()
        .all()
    )

    portfolio_count = db.execute(
        select(func.count(Design.id)).where(
            Design.artist_profile_id == artist_profile.id,
            Design.status == DesignStatus.PUBLISHED.value,
            Design.deleted_at.is_(None),
        )
    ).scalar_one()

    portfolio_designs = (
        db.execute(
            select(Design)
            .where(
                Design.artist_profile_id == artist_profile.id,
                Design.status == DesignStatus.PUBLISHED.value,
                Design.deleted_at.is_(None),
            )
            .order_by(Design.created_at.desc(), Design.id.desc())
            .limit(PORTFOLIO_PREVIEW_LIMIT)
        )
        .scalars()
        .all()
    )

    return ArtistPublicProfileOut(
        id=artist_profile.id,
        user_id=artist_profile.user_id,
        display_name=_display_name(artist_profile, profile),
        professional_name=artist_profile.professional_name,
        business_name=artist_profile.business_name,
        headline=artist_profile.headline,
        bio=artist_profile.bio,
        years_experience=artist_profile.years_experience,
        city=artist_profile.city,
        country=artist_profile.country,
        service_areas=artist_profile.service_areas or [],
        languages=artist_profile.languages or [],
        profile_image_url=artist_profile.profile_image_url,
        cover_image_url=artist_profile.cover_image_url,
        social_links=artist_profile.social_links or {},
        is_verified=artist_profile.verification_status == ArtistVerificationStatus.APPROVED.value,
        rating_average=float(artist_profile.rating_average),
        rating_count=artist_profile.rating_count,
        follower_count=artist_profile.follower_count,
        is_followed=is_following(db, user_id=viewer_user_id, artist_profile_id=artist_profile.id),
        is_accepting_bookings=artist_profile.is_accepting_bookings,
        services=[service_out(s) for s in services],
        availability_preview=[
            ArtistAvailabilitySlotOut(
                day_of_week=slot.day_of_week, start_time=slot.start_time, end_time=slot.end_time
            )
            for slot in availability
        ],
        portfolio_preview=summaries_for_designs(db, list(portfolio_designs)),
        portfolio_count=portfolio_count,
    )
