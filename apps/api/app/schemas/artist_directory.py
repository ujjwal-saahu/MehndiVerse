"""Public artist directory/profile, self-service services, and portfolio
analytics — see docs/artist-directory.md.
"""

import re
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.design import DesignSummaryOut, PageInfo

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_VALID_PRICING_TYPES = {"fixed", "range", "custom_quote"}


class ArtistServiceOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    pricing_type: str
    price_amount: float | None
    price_min: float | None
    price_max: float | None
    currency: str
    duration_minutes: int | None
    customer_capacity: int | None
    deposit_required: bool
    deposit_amount: float | None
    travel_charge_amount: float | None
    cancellation_policy: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


def validate_pricing_consistency(
    *,
    pricing_type: str,
    price_amount: float | None,
    price_min: float | None,
    price_max: float | None,
) -> None:
    """Shared by create (full payload) and update (payload merged onto the
    existing row) — a service's price shape must match its `pricing_type`,
    whichever fields a particular request happened to touch."""
    if pricing_type == "fixed":
        if price_amount is None:
            raise ValueError("price_amount is required for a fixed-price service.")
        if price_min is not None or price_max is not None:
            raise ValueError("price_min/price_max don't apply to a fixed-price service.")
    elif pricing_type == "range":
        if price_min is None or price_max is None:
            raise ValueError(
                "price_min and price_max are both required for a range-priced service."
            )
        if price_amount is not None:
            raise ValueError("price_amount doesn't apply to a range-priced service.")
        if price_max < price_min:
            raise ValueError("price_max must be greater than or equal to price_min.")
    else:  # custom_quote
        if price_amount is not None or price_min is not None or price_max is not None:
            raise ValueError("A custom-quote service has no price_amount/price_min/price_max.")


class ArtistServiceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=3000)
    pricing_type: str
    price_amount: float | None = Field(default=None, ge=0)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    currency: str
    duration_minutes: int | None = Field(default=None, gt=0)
    customer_capacity: int | None = Field(default=None, gt=0)
    deposit_required: bool = False
    deposit_amount: float | None = Field(default=None, ge=0)
    travel_charge_amount: float | None = Field(default=None, ge=0)
    cancellation_policy: str | None = Field(default=None, max_length=3000)

    @field_validator("pricing_type")
    @classmethod
    def _validate_pricing_type(cls, value: str) -> str:
        if value not in _VALID_PRICING_TYPES:
            raise ValueError(
                f"pricing_type must be one of: {', '.join(sorted(_VALID_PRICING_TYPES))}"
            )
        return value

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        upper = value.strip().upper()
        if not _CURRENCY_RE.match(upper):
            raise ValueError("currency must be a 3-letter ISO 4217 code (e.g. INR, USD).")
        return upper

    @model_validator(mode="after")
    def _check_pricing_consistency(self) -> "ArtistServiceCreateRequest":
        validate_pricing_consistency(
            pricing_type=self.pricing_type,
            price_amount=self.price_amount,
            price_min=self.price_min,
            price_max=self.price_max,
        )
        return self


class ArtistServiceUpdateRequest(BaseModel):
    """Partial update — only fields explicitly present are applied
    (`exclude_unset`). Pricing consistency is re-checked in the route after
    merging onto the existing row, since a partial payload alone can't be
    validated in isolation (e.g. changing just `price_max`)."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=3000)
    pricing_type: str | None = None
    price_amount: float | None = Field(default=None, ge=0)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    currency: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    customer_capacity: int | None = Field(default=None, gt=0)
    deposit_required: bool | None = None
    deposit_amount: float | None = Field(default=None, ge=0)
    travel_charge_amount: float | None = Field(default=None, ge=0)
    cancellation_policy: str | None = Field(default=None, max_length=3000)
    is_active: bool | None = None

    @field_validator("pricing_type")
    @classmethod
    def _validate_pricing_type(cls, value: str | None) -> str | None:
        if value is not None and value not in _VALID_PRICING_TYPES:
            raise ValueError(
                f"pricing_type must be one of: {', '.join(sorted(_VALID_PRICING_TYPES))}"
            )
        return value

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        upper = value.strip().upper()
        if not _CURRENCY_RE.match(upper):
            raise ValueError("currency must be a 3-letter ISO 4217 code (e.g. INR, USD).")
        return upper


class ArtistAvailabilitySlotOut(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time


class ArtistPublicProfileOut(BaseModel):
    """The public-facing artist profile — deliberately excludes anything from
    `ArtistProfileOut` (app/schemas/artist.py) that's private to the owner or
    staff: contact_email/phone, verification internals (submitted_at,
    rejection_reason, missing_requirements, ...). See
    docs/artist-directory.md#public-profile-vs-owner-profile."""

    id: UUID
    # The owning account's id — not otherwise private, and needed so a viewer
    # can report the artist as a user (see
    # docs/community-and-trust.md#5-reports-enter-a-moderation-queue).
    user_id: UUID
    display_name: str
    professional_name: str | None
    business_name: str | None
    headline: str | None
    bio: str | None
    years_experience: int | None
    city: str | None
    country: str | None
    service_areas: list[str]
    languages: list[str]
    profile_image_url: str | None
    cover_image_url: str | None
    social_links: dict[str, str]
    is_verified: bool
    rating_average: float
    rating_count: int
    follower_count: int
    is_followed: bool
    is_accepting_bookings: bool
    services: list[ArtistServiceOut]
    availability_preview: list[ArtistAvailabilitySlotOut]
    portfolio_preview: list[DesignSummaryOut]
    portfolio_count: int


class ArtistDirectoryItemOut(BaseModel):
    id: UUID
    display_name: str
    headline: str | None
    avatar_url: str | None
    city: str | None
    country: str | None
    years_experience: int | None
    is_verified: bool
    rating_average: float
    rating_count: int
    is_accepting_bookings: bool


class ArtistDirectoryListOut(BaseModel):
    items: list[ArtistDirectoryItemOut]
    page_info: PageInfo


class PortfolioAnalyticsOut(BaseModel):
    total_designs: int
    published_designs: int
    total_views: int
    total_likes: int
    total_saves: int
    top_designs: list[DesignSummaryOut]
