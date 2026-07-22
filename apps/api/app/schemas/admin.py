"""Admin-dashboard request/response schemas — see docs/admin-dashboard.md.

Domain schemas that already had a natural home (`CategoryOut`, `RefundOut`,
`BookingSummaryOut`, ...) are reused directly rather than duplicated here;
this file holds what's new for Phase 17: dashboard overview, user/design/
booking/review admin list+moderation shapes, tags, the three new marketing
domains (banners/featured collections/notification campaigns), the global
audit-log viewer, and system settings.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminPageInfo(BaseModel):
    """Offset-pagination page info — see app/core/admin_listing.py for why
    this (not the cursor-based `PageInfo` in app/schemas/design.py) is what
    every admin list endpoint returns."""

    page: int
    page_size: int
    total: int
    total_pages: int


# --- Dashboard overview -------------------------------------------------------


class DashboardOverviewOut(BaseModel):
    pending_artist_verifications: int
    pending_reports: int
    pending_refunds: int
    disputed_bookings: int
    total_users: int
    total_artists: int
    total_designs: int
    total_bookings: int


# --- User management -----------------------------------------------------------


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    display_name: str | None
    created_at: datetime
    last_login_at: datetime | None


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    page_info: AdminPageInfo


class UserSuspendRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


# --- Design moderation -----------------------------------------------------------


class AdminDesignListItemOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    artist_profile_id: uuid.UUID | None
    artist_display_name: str | None
    is_featured: bool
    view_count: int
    like_count: int
    created_at: datetime


class AdminDesignListOut(BaseModel):
    items: list[AdminDesignListItemOut]
    page_info: AdminPageInfo


class DesignModerateRequest(BaseModel):
    action: str = Field(description="One of: publish, unpublish, archive, flag")
    reason: str = Field(min_length=1, max_length=1000)


# --- Tags ------------------------------------------------------------------------


class TagOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class TagListOut(BaseModel):
    items: list[TagOut]
    page_info: AdminPageInfo


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50)


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    slug: str | None = Field(default=None, min_length=1, max_length=50)


# --- Booking management / disputes ------------------------------------------------


class AdminBookingListItemOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_display_name: str | None
    artist_profile_id: uuid.UUID
    artist_display_name: str | None
    status: str
    requested_date: date | None
    total_amount: float | None
    currency: str
    created_at: datetime


class AdminBookingListOut(BaseModel):
    items: list[AdminBookingListItemOut]
    page_info: AdminPageInfo


class BookingDisputeRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class BookingDisputeResolveRequest(BaseModel):
    to_status: str = Field(description="One of: completed, cancelled, refunded")
    reason: str = Field(min_length=1, max_length=1000)


# --- Payments ----------------------------------------------------------------------


class AdminPaymentListItemOut(BaseModel):
    id: uuid.UUID
    # Nullable: a subscription payment (payment_type="subscription") has
    # subscription_id set and booking_id null instead — see
    # docs/subscriptions-and-entitlements.md#subscription-checkout-reuses-
    # payments.
    booking_id: uuid.UUID | None
    subscription_id: uuid.UUID | None
    payer_id: uuid.UUID
    amount: int
    currency: str
    status: str
    payment_type: str
    provider: str
    created_at: datetime


class AdminPaymentListOut(BaseModel):
    items: list[AdminPaymentListItemOut]
    page_info: AdminPageInfo


class AdminRefundListItemOut(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    amount: int
    currency: str
    reason: str | None
    status: str
    requested_at: datetime
    processed_at: datetime | None


class AdminRefundListOut(BaseModel):
    items: list[AdminRefundListItemOut]
    page_info: AdminPageInfo


# --- Review moderation --------------------------------------------------------------


class ReviewModerateRequest(BaseModel):
    action: str = Field(description="One of: flag, unflag, remove, restore")
    reason: str = Field(min_length=1, max_length=1000)


class AdminReviewListItemOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    customer_display_name: str | None
    artist_profile_id: uuid.UUID
    rating: int
    body: str | None
    is_flagged: bool
    is_deleted: bool
    created_at: datetime


class AdminReviewListOut(BaseModel):
    items: list[AdminReviewListItemOut]
    page_info: AdminPageInfo


# --- Promotional banners --------------------------------------------------------------


class PromoBannerOut(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: str | None
    image_url: str
    link_url: str | None
    is_active: bool
    starts_at: datetime | None
    ends_at: datetime | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PromoBannerListOut(BaseModel):
    items: list[PromoBannerOut]
    page_info: AdminPageInfo


class PromoBannerCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    subtitle: str | None = Field(default=None, max_length=300)
    image_url: str = Field(min_length=1, max_length=2048)
    link_url: str | None = Field(default=None, max_length=2048)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    sort_order: int = 0


class PromoBannerUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    subtitle: str | None = Field(default=None, max_length=300)
    image_url: str | None = Field(default=None, min_length=1, max_length=2048)
    link_url: str | None = Field(default=None, max_length=2048)
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    sort_order: int | None = None


# --- Featured collections --------------------------------------------------------------


class FeaturedCollectionItemOut(BaseModel):
    id: uuid.UUID
    design_id: uuid.UUID
    sort_order: int


class FeaturedCollectionOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    cover_image_url: str | None
    is_active: bool
    sort_order: int
    items: list[FeaturedCollectionItemOut]
    created_at: datetime
    updated_at: datetime


class FeaturedCollectionListOut(BaseModel):
    items: list[FeaturedCollectionOut]
    page_info: AdminPageInfo


class FeaturedCollectionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    sort_order: int = 0


class FeaturedCollectionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    cover_image_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class FeaturedCollectionAddItemRequest(BaseModel):
    design_id: uuid.UUID
    sort_order: int = 0


# --- Notification campaigns --------------------------------------------------------------


class NotificationCampaignOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    target_role: str | None
    status: str
    recipient_count: int | None
    sent_at: datetime | None
    created_at: datetime


class NotificationCampaignListOut(BaseModel):
    items: list[NotificationCampaignOut]
    page_info: AdminPageInfo


class NotificationCampaignCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    body: str = Field(min_length=1, max_length=2000)
    target_role: str | None = None


# --- Audit-log viewer --------------------------------------------------------------


class GlobalAuditLogEntryOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_display_name: str | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    created_at: datetime


class GlobalAuditLogListOut(BaseModel):
    items: list[GlobalAuditLogEntryOut]
    page_info: AdminPageInfo


# --- System settings --------------------------------------------------------------


class SystemSettingOut(BaseModel):
    id: uuid.UUID
    key: str
    value: Any
    description: str | None
    is_public: bool
    updated_by: uuid.UUID | None
    updated_at: datetime


class SystemSettingListOut(BaseModel):
    items: list[SystemSettingOut]


class SystemSettingUpsertRequest(BaseModel):
    value: Any
    description: str | None = Field(default=None, max_length=500)
    is_public: bool = False
