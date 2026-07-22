"""Coupon validation and redemption — see
docs/subscriptions-and-entitlements.md#coupons.

Abuse prevention is enforced at two layers: `Coupon.max_redemptions` /
`valid_from`/`valid_until`/`is_active` are checked here at validation time
(so a stale or exhausted coupon is rejected with a clear message), and the
database's own `uq_coupon_redemptions_coupon_user` unique constraint
(app/db/models/marketing.py) is what actually stops the same user redeeming
the same coupon twice — even a race between two concurrent requests can't
double-redeem, because the second insert simply fails uniqueness (the same
"insert first, treat a conflict as already-done" pattern
app/services/payments/service.py::handle_webhook uses for webhook dedup).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import CouponDiscountType
from app.db.models.marketing import Coupon, CouponRedemption


def get_coupon_by_code(db: Session, code: str) -> Coupon | None:
    return db.execute(
        select(Coupon).where(Coupon.code == code.strip().upper())
    ).scalar_one_or_none()


def price_coupon(
    db: Session, *, code: str, user_id: uuid.UUID, amount: float
) -> tuple[Coupon, float]:
    """Validates a coupon against a specific checkout amount and returns
    `(coupon, discount_amount)`. Raises `AppError` if it isn't currently
    redeemable by this user — never trusts a client-computed discount."""
    coupon = get_coupon_by_code(db, code)
    if coupon is None:
        raise AppError("Invalid coupon code.", status_code=404)

    now = datetime.now(UTC)
    if not coupon.is_active:
        raise AppError("This coupon is no longer active.", status_code=422)
    if coupon.valid_from > now:
        raise AppError("This coupon is not yet valid.", status_code=422)
    if coupon.valid_until is not None and coupon.valid_until < now:
        raise AppError("This coupon has expired.", status_code=422)
    if coupon.max_redemptions is not None and coupon.redemption_count >= coupon.max_redemptions:
        raise AppError("This coupon has reached its redemption limit.", status_code=422)

    already_redeemed = db.execute(
        select(CouponRedemption.id).where(
            CouponRedemption.coupon_id == coupon.id, CouponRedemption.user_id == user_id
        )
    ).first()
    if already_redeemed is not None:
        raise AppError("You've already used this coupon.", status_code=409)

    if coupon.discount_type == CouponDiscountType.PERCENTAGE.value:
        discount = amount * (float(coupon.discount_value) / 100)
    else:
        discount = float(coupon.discount_value)
    return coupon, min(discount, amount)


def redeem_coupon(
    db: Session,
    coupon: Coupon,
    *,
    user_id: uuid.UUID,
    discount_applied: float,
    booking_id: uuid.UUID | None = None,
    subscription_id: uuid.UUID | None = None,
) -> CouponRedemption:
    redemption = CouponRedemption(
        coupon_id=coupon.id,
        user_id=user_id,
        booking_id=booking_id,
        subscription_id=subscription_id,
        discount_applied=discount_applied,
        redeemed_at=datetime.now(UTC),
    )
    db.add(redemption)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as exc:
        raise AppError("You've already used this coupon.", status_code=409) from exc

    coupon.redemption_count += 1
    db.add(coupon)
    return redemption
