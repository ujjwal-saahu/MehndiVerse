"""Request/response models for subscriptions and entitlements — see
docs/subscriptions-and-entitlements.md.

`price_amount`/`discount_applied`-style money fields here are decimal major
units (a human-facing list price), not the integer-minor-unit ledger
convention `payments.amount` uses — see
docs/payments.md#7-integer-minor-currency-units. `CheckoutOut` mirrors
`PaymentOrderOut` (app/schemas/payment.py) exactly, in minor units, because
it *is* a payment order under the hood.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubscriptionPlanOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    target_role: str
    price_amount: float
    currency: str
    billing_interval: str
    features: dict[str, Any] | None
    is_active: bool


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plan: SubscriptionPlanOut
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    grace_period_ends_at: datetime | None
    started_at: datetime
    cancelled_at: datetime | None


class SubscriptionStatusHistoryOut(BaseModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class MySubscriptionOut(BaseModel):
    subscription: SubscriptionOut | None
    entitlements: dict[str, Any]


class CheckoutRequest(BaseModel):
    plan_id: uuid.UUID
    coupon_code: str | None = Field(default=None, max_length=50)
    idempotency_key: str | None = Field(default=None, max_length=255)


class CheckoutOut(BaseModel):
    payment_id: uuid.UUID
    provider: str
    provider_order_id: str
    provider_key_id: str
    amount: int
    currency: str
    status: str


class CancelSubscriptionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class BillingHistoryItemOut(BaseModel):
    payment_id: uuid.UUID
    plan_name: str | None
    amount: int
    currency: str
    status: str
    failure_reason: str | None
    paid_at: datetime | None
    created_at: datetime
