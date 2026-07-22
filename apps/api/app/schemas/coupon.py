"""Request/response models for coupon validation, redemption, and staff
management — see docs/subscriptions-and-entitlements.md#coupons."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    plan_id: uuid.UUID


class CouponValidateOut(BaseModel):
    valid: bool
    message: str | None = None
    discount_amount: float | None = None
    final_amount: float | None = None


class CouponOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str | None
    discount_type: str
    discount_value: float
    currency: str | None
    max_redemptions: int | None
    redemption_count: int
    min_booking_amount: float | None
    valid_from: datetime
    valid_until: datetime | None
    is_active: bool


class CouponListOut(BaseModel):
    items: list[CouponOut]


class CouponCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    discount_type: str
    discount_value: float = Field(gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    max_redemptions: int | None = Field(default=None, gt=0)
    min_booking_amount: float | None = Field(default=None, ge=0)
    valid_from: datetime
    valid_until: datetime | None = None


class CouponUpdateRequest(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    valid_until: datetime | None = None
    max_redemptions: int | None = Field(default=None, gt=0)
