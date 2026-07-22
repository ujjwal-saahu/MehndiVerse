"""Staff-side coupon management — see
docs/subscriptions-and-entitlements.md#coupons.

`Coupon.created_by` (Phase 2 schema) implies staff-authored coupons, but no
CRUD surface existed anywhere until now — the same "first place this table
gets a route" situation `admin_tags.py` was in for `Tag`. Mirrors that
file's shape.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError
from app.db.enums import CouponDiscountType
from app.db.models.marketing import Coupon
from app.db.session import get_db_session
from app.schemas.coupon import CouponCreateRequest, CouponListOut, CouponOut, CouponUpdateRequest

router = APIRouter(prefix="/admin/coupons", tags=["admin-coupons"])

_STAFF_ROLES = ("admin", "super_admin")


def _coupon_out(coupon: Coupon) -> CouponOut:
    return CouponOut(
        id=coupon.id,
        code=coupon.code,
        description=coupon.description,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value),
        currency=coupon.currency,
        max_redemptions=coupon.max_redemptions,
        redemption_count=coupon.redemption_count,
        min_booking_amount=coupon.min_booking_amount,
        valid_from=coupon.valid_from,
        valid_until=coupon.valid_until,
        is_active=coupon.is_active,
    )


def _get_coupon_or_404(db: Session, coupon_id: uuid.UUID) -> Coupon:
    coupon = db.get(Coupon, coupon_id)
    if coupon is None:
        raise AppError("Coupon not found.", status_code=404)
    return coupon


@router.get("", response_model=CouponListOut)
def list_coupons(
    current: AuthenticatedUser = Depends(require_roles(*_STAFF_ROLES)),
    db: Session = Depends(get_db_session),
) -> CouponListOut:
    coupons = db.execute(select(Coupon).order_by(Coupon.created_at.desc())).scalars().all()
    return CouponListOut(items=[_coupon_out(c) for c in coupons])


@router.post("", response_model=CouponOut, status_code=201)
def create_coupon(
    payload: CouponCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_STAFF_ROLES)),
    db: Session = Depends(get_db_session),
) -> CouponOut:
    if payload.discount_type not in {member.value for member in CouponDiscountType}:
        raise AppError(f"Unknown discount_type: {payload.discount_type!r}", status_code=422)
    code = payload.code.strip().upper()
    if db.execute(select(Coupon.id).where(Coupon.code == code)).first() is not None:
        raise AppError("A coupon with this code already exists.", status_code=409)

    coupon = Coupon(
        code=code,
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        currency=payload.currency,
        max_redemptions=payload.max_redemptions,
        min_booking_amount=payload.min_booking_amount,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        created_by=current.user.id,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return _coupon_out(coupon)


@router.patch("/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: uuid.UUID,
    payload: CouponUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_STAFF_ROLES)),
    db: Session = Depends(get_db_session),
) -> CouponOut:
    coupon = _get_coupon_or_404(db, coupon_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(coupon, field, value)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return _coupon_out(coupon)
