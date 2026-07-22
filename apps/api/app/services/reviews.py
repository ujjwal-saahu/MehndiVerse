"""Booking reviews and artist rating aggregation — see
docs/community-and-trust.md#3-review-a-completed-booking and
#4-artist-rating-aggregation.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import BookingStatus
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.review import Review
from app.services.blocking import is_blocked_either_direction

MIN_RATING = 1
MAX_RATING = 5
MAX_REVIEW_BODY_LENGTH = 3000


def recompute_artist_rating(db: Session, artist_profile_id: uuid.UUID) -> None:
    """The aggregate is always *recomputed from the reviews table itself*,
    never incrementally adjusted — see
    docs/community-and-trust.md#4-artist-rating-aggregation for why this is
    the safer choice for a value that must "remain consistent": a running
    counter can drift (a missed decrement, a double-counted edit); a full
    recompute inside the same transaction as the write that triggered it
    never can, by construction."""
    average, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.artist_profile_id == artist_profile_id, Review.deleted_at.is_(None)
        )
    ).one()
    new_average = round(float(average), 2) if average is not None else 0
    db.execute(
        update(ArtistProfile)
        .where(ArtistProfile.id == artist_profile_id)
        .values(rating_average=new_average, rating_count=count)
    )


def create_review(
    db: Session, booking: Booking, *, customer_id: uuid.UUID, rating: int, body: str | None
) -> Review:
    if booking.customer_id != customer_id:
        raise AppError("Only the customer on this booking can review it.", status_code=403)
    if booking.status != BookingStatus.COMPLETED.value:
        raise AppError(
            "You can only review a booking once the service has been completed.", status_code=422
        )
    if not (MIN_RATING <= rating <= MAX_RATING):
        raise AppError(f"Rating must be between {MIN_RATING} and {MAX_RATING}.", status_code=422)
    if body is not None and len(body) > MAX_REVIEW_BODY_LENGTH:
        raise AppError(
            f"A review cannot exceed {MAX_REVIEW_BODY_LENGTH} characters.", status_code=422
        )

    existing = db.execute(select(Review.id).where(Review.booking_id == booking.id)).first()
    if existing is not None:
        raise AppError("This booking has already been reviewed.", status_code=409)

    artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
    if artist_profile is not None and is_blocked_either_direction(
        db, customer_id, artist_profile.user_id
    ):
        raise AppError(
            "You can't review this artist — one of you has blocked the other.", status_code=403
        )

    review = Review(
        booking_id=booking.id,
        customer_id=customer_id,
        artist_profile_id=booking.artist_profile_id,
        rating=rating,
        body=body,
    )
    db.add(review)
    db.flush()
    recompute_artist_rating(db, booking.artist_profile_id)
    return review


def list_reviews_for_artist(
    db: Session, artist_profile_id: uuid.UUID, *, limit: int = 20
) -> list[Review]:
    return list(
        db.execute(
            select(Review)
            .where(Review.artist_profile_id == artist_profile_id, Review.deleted_at.is_(None))
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
