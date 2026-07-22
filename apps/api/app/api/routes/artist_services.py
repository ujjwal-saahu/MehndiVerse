"""Self-service management of an artist's bookable services — see
docs/artist-directory.md#services.

Open to any `artist`/`verified_artist` (not gated on verification status),
mirroring app/api/routes/designs.py's `_CREATE_ROLES` precedent — an artist
can draft their service list before their application is approved, the same
way they can draft portfolio designs.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, AuthorizationError
from app.db.models.artist import ArtistProfile, ArtistService
from app.db.session import get_db_session
from app.schemas.artist_directory import (
    ArtistServiceCreateRequest,
    ArtistServiceOut,
    ArtistServiceUpdateRequest,
    validate_pricing_consistency,
)
from app.services.artist_directory import service_out

router = APIRouter(prefix="/artist/services", tags=["artist-services"])

_SERVICE_ROLES = ("artist", "verified_artist")


def _get_own_profile_or_404(db: Session, current: AuthenticatedUser) -> ArtistProfile:
    profile = db.execute(
        select(ArtistProfile).where(
            ArtistProfile.user_id == current.user.id, ArtistProfile.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("You need an artist profile before managing services.", status_code=404)
    return profile


def _get_own_service_or_404(
    db: Session, service_id: uuid.UUID, profile: ArtistProfile
) -> ArtistService:
    service = db.execute(
        select(ArtistService).where(
            ArtistService.id == service_id, ArtistService.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if service is None:
        raise AppError("Service not found.", status_code=404)
    if service.artist_profile_id != profile.id:
        raise AuthorizationError("You do not own this service.")
    return service


@router.get("", response_model=list[ArtistServiceOut])
def list_my_services(
    current: AuthenticatedUser = Depends(require_roles(*_SERVICE_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[ArtistServiceOut]:
    profile = _get_own_profile_or_404(db, current)
    services = (
        db.execute(
            select(ArtistService)
            .where(
                ArtistService.artist_profile_id == profile.id,
                ArtistService.deleted_at.is_(None),
            )
            .order_by(ArtistService.created_at)
        )
        .scalars()
        .all()
    )
    return [service_out(s) for s in services]


@router.post("", response_model=ArtistServiceOut, status_code=201)
def create_my_service(
    payload: ArtistServiceCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SERVICE_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistServiceOut:
    profile = _get_own_profile_or_404(db, current)

    service = ArtistService(
        artist_profile_id=profile.id,
        name=payload.name,
        description=payload.description,
        pricing_type=payload.pricing_type,
        price_amount=payload.price_amount,
        price_min=payload.price_min,
        price_max=payload.price_max,
        currency=payload.currency,
        duration_minutes=payload.duration_minutes,
        customer_capacity=payload.customer_capacity,
        deposit_required=payload.deposit_required,
        deposit_amount=payload.deposit_amount,
        travel_charge_amount=payload.travel_charge_amount,
        cancellation_policy=payload.cancellation_policy,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service_out(service)


@router.patch("/{service_id}", response_model=ArtistServiceOut)
def update_my_service(
    service_id: uuid.UUID,
    payload: ArtistServiceUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SERVICE_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistServiceOut:
    profile = _get_own_profile_or_404(db, current)
    service = _get_own_service_or_404(db, service_id, profile)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(service, field, value)

    try:
        validate_pricing_consistency(
            pricing_type=service.pricing_type,
            price_amount=service.price_amount,
            price_min=service.price_min,
            price_max=service.price_max,
        )
    except ValueError as exc:
        raise AppError(str(exc), status_code=422) from exc

    db.add(service)
    db.commit()
    db.refresh(service)
    return service_out(service)
