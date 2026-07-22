"""Customer/artist-facing coupon validation — see
docs/subscriptions-and-entitlements.md#coupons.

Validation only *previews* a discount; it never redeems (redemption happens
as part of `create_subscription_checkout`, see app/services/subscriptions.py)
so a user can check a code before committing to checkout without burning
their one-per-coupon redemption on a mistyped code."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError
from app.db.models.subscription import SubscriptionPlan
from app.db.session import get_db_session
from app.schemas.coupon import CouponValidateOut, CouponValidateRequest
from app.services.coupons import price_coupon

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("/validate", response_model=CouponValidateOut)
def validate_coupon(
    payload: CouponValidateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CouponValidateOut:
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if plan is None:
        raise AppError("Plan not found.", status_code=404)

    try:
        _coupon, discount = price_coupon(
            db, code=payload.code, user_id=current.user.id, amount=float(plan.price_amount)
        )
    except AppError as exc:
        return CouponValidateOut(valid=False, message=exc.message)

    return CouponValidateOut(
        valid=True,
        discount_amount=discount,
        final_amount=max(float(plan.price_amount) - discount, 0.0),
    )
