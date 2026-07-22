"""Staff-side review moderation — see docs/admin-dashboard.md#review-
moderation. `flag`/`unflag` mark a review for attention without hiding it;
`remove`/`restore` soft-delete/undelete it (see `Review`'s `SoftDeleteMixin`)
— either way, `recompute_artist_rating()` re-runs afterward so
`ArtistProfile.rating_average`/`rating_count` never drift from what
customers can actually see, mirroring the same recompute-on-every-write
discipline `app/services/reviews.py::create_review` already follows (see
docs/community-and-trust.md#4-artist-rating-aggregation).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import (
    normalize_pagination,
    paginate,
    resolve_sort_column,
    resolve_sort_direction,
)
from app.core.exceptions import AppError
from app.db.models.review import Review
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminPageInfo,
    AdminReviewListItemOut,
    AdminReviewListOut,
    ReviewModerateRequest,
)
from app.services.audit import record_audit_log
from app.services.reviews import recompute_artist_rating

router = APIRouter(prefix="/admin/reviews", tags=["admin-reviews"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_SORT_COLUMNS = {
    "created_at": Review.created_at,
    "rating": Review.rating,
}

_ACTIONS = frozenset({"flag", "unflag", "remove", "restore"})


def _get_review_or_404(db: Session, review_id: uuid.UUID) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise AppError("Review not found.", status_code=404)
    return review


def _review_item_out(review: Review, customer_name: str | None) -> AdminReviewListItemOut:
    return AdminReviewListItemOut(
        id=review.id,
        booking_id=review.booking_id,
        customer_id=review.customer_id,
        customer_display_name=customer_name,
        artist_profile_id=review.artist_profile_id,
        rating=review.rating,
        body=review.body,
        is_flagged=review.is_flagged,
        is_deleted=review.deleted_at is not None,
        created_at=review.created_at,
    )


@router.get("", response_model=AdminReviewListOut)
def list_reviews(
    is_flagged: bool | None = None,
    artist_profile_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminReviewListOut:
    page, page_size = normalize_pagination(page, page_size)
    sort_key, sort_column = resolve_sort_column(
        sort_by, columns=_SORT_COLUMNS, default_key="created_at"
    )
    direction = resolve_sort_direction(sort_dir)

    # Includes soft-deleted (removed) reviews — staff need to see what was
    # removed, and why, not just the currently-visible set.
    stmt = select(Review)
    if is_flagged is not None:
        stmt = stmt.where(Review.is_flagged.is_(is_flagged))
    if artist_profile_id is not None:
        stmt = stmt.where(Review.artist_profile_id == artist_profile_id)

    ordered = stmt.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), Review.id
    )
    result = paginate(db, ordered, page=page, page_size=page_size)

    customer_ids = [r.customer_id for r in result.items]
    names: dict[uuid.UUID, str | None] = {}
    if customer_ids:
        rows = db.execute(
            select(Profile.user_id, Profile.display_name).where(
                Profile.user_id.in_(set(customer_ids))
            )
        ).all()
        names = {row.user_id: row.display_name for row in rows}

    return AdminReviewListOut(
        items=[_review_item_out(r, names.get(r.customer_id)) for r in result.items],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("/{review_id}/moderate", response_model=AdminReviewListItemOut)
def moderate_review(
    review_id: uuid.UUID,
    payload: ReviewModerateRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminReviewListItemOut:
    if payload.action not in _ACTIONS:
        raise AppError(
            f"Unknown moderation action '{payload.action}'. Choose one of: "
            f"{', '.join(sorted(_ACTIONS))}.",
            status_code=422,
        )
    review = _get_review_or_404(db, review_id)

    before_state = {"is_flagged": review.is_flagged, "is_deleted": review.deleted_at is not None}
    if payload.action == "flag":
        review.is_flagged = True
    elif payload.action == "unflag":
        review.is_flagged = False
    elif payload.action == "remove":
        review.deleted_at = datetime.now(UTC)
    else:  # restore
        review.deleted_at = None
    db.add(review)

    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action=f"review.moderate.{payload.action}",
        entity_type="reviews",
        entity_id=review.id,
        before_state=before_state,
        after_state={
            "is_flagged": review.is_flagged,
            "is_deleted": review.deleted_at is not None,
            "reason": payload.reason,
        },
    )
    # Removing/restoring changes which reviews count toward the aggregate;
    # flag/unflag doesn't affect it but recomputing is cheap and keeps this
    # one code path simple rather than special-casing which actions need it.
    recompute_artist_rating(db, review.artist_profile_id)
    db.commit()
    db.refresh(review)

    customer_name = db.execute(
        select(Profile.display_name).where(Profile.user_id == review.customer_id)
    ).scalar_one_or_none()
    return _review_item_out(review, customer_name)
