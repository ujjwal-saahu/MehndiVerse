"""Staff-only payment oversight: platform-wide payment/refund review
(Phase 17 — see docs/admin-dashboard.md#payment-review and #refund-review)
plus the pre-existing refund approval/rejection and payout-batch creation
(docs/payments.md#9 and #6). Approving a refund is the point where money
actually moves (a real provider API call), so it's staff-gated rather than
self-service — either party can *request* a refund
(app/api/routes/payments.py), but only staff can approve or reject it.
"""

import uuid

from fastapi import APIRouter, Depends
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
from app.db.enums import PaymentStatus, RefundStatus
from app.db.models.payment import Payment, Refund
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminPageInfo,
    AdminPaymentListItemOut,
    AdminPaymentListOut,
    AdminRefundListItemOut,
    AdminRefundListOut,
)
from app.schemas.payment import PayoutOut, RefundOut, RefundRejectRequest
from app.services.payments.service import approve_refund, create_payout_batch, reject_refund

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_STAFF_ROLES = ("admin", "super_admin")

_PAYMENT_SORT_COLUMNS = {
    "created_at": Payment.created_at,
    "amount": Payment.amount,
    "status": Payment.status,
}
_REFUND_SORT_COLUMNS = {
    "requested_at": Refund.requested_at,
    "amount": Refund.amount,
    "status": Refund.status,
}


def _get_refund_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise AppError("Refund not found.", status_code=404)
    return refund


def _refund_out(refund: Refund) -> RefundOut:
    return RefundOut(
        id=refund.id,
        payment_id=refund.payment_id,
        amount=refund.amount,
        currency=refund.currency,
        reason=refund.reason,
        status=refund.status,
        requested_at=refund.requested_at,
        processed_at=refund.processed_at,
    )


@router.get("", response_model=AdminPaymentListOut)
def list_payments(
    status_filter: str | None = None,
    payment_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminPaymentListOut:
    """Platform-wide payment review — see docs/admin-dashboard.md#payment-
    review. View-only for moderators; only admin/super_admin can act on the
    refund/payout endpoints below."""
    page, page_size = normalize_pagination(page, page_size)
    sort_key, sort_column = resolve_sort_column(
        sort_by, columns=_PAYMENT_SORT_COLUMNS, default_key="created_at"
    )
    direction = resolve_sort_direction(sort_dir)

    stmt = select(Payment)
    if status_filter is not None:
        if status_filter not in {s.value for s in PaymentStatus}:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(Payment.status == status_filter)
    if payment_type is not None:
        stmt = stmt.where(Payment.payment_type == payment_type)

    ordered = stmt.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), Payment.id
    )
    result = paginate(db, ordered, page=page, page_size=page_size)

    return AdminPaymentListOut(
        items=[
            AdminPaymentListItemOut(
                id=p.id,
                booking_id=p.booking_id,
                subscription_id=p.subscription_id,
                payer_id=p.payer_id,
                amount=p.amount,
                currency=p.currency,
                status=p.status,
                payment_type=p.payment_type,
                provider=p.provider,
                created_at=p.created_at,
            )
            for p in result.items
        ],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.get("/refunds", response_model=AdminRefundListOut)
def list_refunds(
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminRefundListOut:
    page, page_size = normalize_pagination(page, page_size)
    sort_key, sort_column = resolve_sort_column(
        sort_by, columns=_REFUND_SORT_COLUMNS, default_key="requested_at"
    )
    direction = resolve_sort_direction(sort_dir)

    stmt = select(Refund)
    if status_filter is not None:
        if status_filter not in {s.value for s in RefundStatus}:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(Refund.status == status_filter)

    ordered = stmt.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), Refund.id
    )
    result = paginate(db, ordered, page=page, page_size=page_size)

    return AdminRefundListOut(
        items=[
            AdminRefundListItemOut(
                id=r.id,
                payment_id=r.payment_id,
                amount=r.amount,
                currency=r.currency,
                reason=r.reason,
                status=r.status,
                requested_at=r.requested_at,
                processed_at=r.processed_at,
            )
            for r in result.items
        ],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("/refunds/{refund_id}/approve", response_model=RefundOut)
def approve_payment_refund(
    refund_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_STAFF_ROLES)),
    db: Session = Depends(get_db_session),
) -> RefundOut:
    refund = _get_refund_or_404(db, refund_id)
    approve_refund(db, refund, approved_by=current.user.id)
    db.commit()
    db.refresh(refund)
    return _refund_out(refund)


@router.post("/refunds/{refund_id}/reject", response_model=RefundOut)
def reject_payment_refund(
    refund_id: uuid.UUID,
    payload: RefundRejectRequest,
    current: AuthenticatedUser = Depends(require_roles(*_STAFF_ROLES)),
    db: Session = Depends(get_db_session),
) -> RefundOut:
    refund = _get_refund_or_404(db, refund_id)
    reject_refund(db, refund, rejected_by=current.user.id, reason=payload.reason)
    db.commit()
    db.refresh(refund)
    return _refund_out(refund)


@router.post("/artists/{artist_profile_id}/payouts", response_model=PayoutOut | None)
def create_artist_payout_batch(
    artist_profile_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_STAFF_ROLES)),
    db: Session = Depends(get_db_session),
) -> PayoutOut | None:
    payout = create_payout_batch(db, artist_profile_id=artist_profile_id)
    db.commit()
    if payout is None:
        return None
    db.refresh(payout)
    return PayoutOut(
        id=payout.id,
        artist_profile_id=payout.artist_profile_id,
        amount=payout.amount,
        currency=payout.currency,
        status=payout.status,
        requested_at=payout.requested_at,
        paid_at=payout.paid_at,
    )
