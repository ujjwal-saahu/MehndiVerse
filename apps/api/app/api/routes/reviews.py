"""Booking reviews — see docs/community-and-trust.md#3-review-a-completed-
booking. `POST /bookings/{id}/reviews` lives here (not bookings.py) for the
same reason comments/payments got their own modules — keeps bookings.py
from growing indefinitely.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.review import Review
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.review import ReviewCreateRequest, ReviewListOut, ReviewOut
from app.services.reviews import create_review, list_reviews_for_artist

router = APIRouter(tags=["reviews"])


def _get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError("Booking not found.", status_code=404)
    return booking


def _get_artist_profile_or_404(db: Session, artist_profile_id: uuid.UUID) -> ArtistProfile:
    profile = db.get(ArtistProfile, artist_profile_id)
    if profile is None or profile.deleted_at is not None:
        raise AppError("Artist not found.", status_code=404)
    return profile


def _display_names(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(set(user_ids)))
    ).all()
    return {row.user_id: row.display_name for row in rows}


def _review_out(review: Review, names: dict[uuid.UUID, str | None]) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        booking_id=review.booking_id,
        customer_id=review.customer_id,
        customer_display_name=names.get(review.customer_id),
        artist_profile_id=review.artist_profile_id,
        rating=review.rating,
        body=review.body,
        created_at=review.created_at,
    )


@router.post("/bookings/{booking_id}/reviews", response_model=ReviewOut, status_code=201)
def review_booking(
    booking_id: uuid.UUID,
    payload: ReviewCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReviewOut:
    booking = _get_booking_or_404(db, booking_id)
    review = create_review(
        db, booking, customer_id=current.user.id, rating=payload.rating, body=payload.body
    )
    db.commit()
    db.refresh(review)
    names = _display_names(db, [review.customer_id])
    return _review_out(review, names)


@router.get("/artists/{artist_profile_id}/reviews", response_model=ReviewListOut)
def list_artist_reviews(
    artist_profile_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ReviewListOut:
    profile = _get_artist_profile_or_404(db, artist_profile_id)
    reviews = list_reviews_for_artist(db, profile.id)
    names = _display_names(db, [r.customer_id for r in reviews])
    return ReviewListOut(
        items=[_review_out(r, names) for r in reviews],
        rating_average=float(profile.rating_average),
        rating_count=profile.rating_count,
    )
