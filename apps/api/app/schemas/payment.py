"""Request/response models for booking payments — see docs/payments.md.
Amounts in responses are integer minor units (see
docs/payments.md#7-integer-minor-currency-units) — clients are responsible
for dividing by 100 (or whatever the currency's minor-unit factor is) for
display, exactly as every payment provider's own API works.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreatePaymentOrderRequest(BaseModel):
    payment_type: str
    idempotency_key: str | None = Field(default=None, max_length=255)


class PaymentOrderOut(BaseModel):
    payment_id: uuid.UUID
    provider: str
    provider_order_id: str
    provider_key_id: str
    amount: int
    currency: str
    status: str


class PaymentOut(BaseModel):
    id: uuid.UUID
    # Nullable: a subscription payment has subscription_id set and
    # booking_id null instead — see
    # docs/subscriptions-and-entitlements.md#subscription-checkout-reuses-
    # payments. Always non-null for payments returned from this booking-
    # scoped route, but the underlying column itself is nullable.
    booking_id: uuid.UUID | None
    payer_id: uuid.UUID
    amount: int
    currency: str
    provider: str
    payment_type: str
    status: str
    failure_reason: str | None
    commission_amount: int | None
    net_amount: int | None
    paid_at: datetime | None
    created_at: datetime


class PaymentReceiptOut(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    payment_type: str
    amount: int
    currency: str
    status: str
    paid_at: datetime | None
    provider: str
    provider_payment_id: str | None
    artist_display_name: str | None
    service_name: str | None


class RefundRequestRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class RefundOut(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    amount: int
    currency: str
    reason: str | None
    status: str
    requested_at: datetime
    processed_at: datetime | None


class RefundRejectRequest(BaseModel):
    # Mandatory — see docs/admin-dashboard.md#mandatory-reasons.
    reason: str = Field(min_length=1, max_length=1000)


class ArtistEarningOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    payment_id: uuid.UUID
    gross_amount: int
    commission_amount: int
    net_amount: int
    currency: str
    payout_id: uuid.UUID | None
    created_at: datetime


class PayoutOut(BaseModel):
    id: uuid.UUID
    artist_profile_id: uuid.UUID
    amount: int
    currency: str
    status: str
    requested_at: datetime
    paid_at: datetime | None
