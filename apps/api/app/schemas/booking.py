"""Request/response models for the booking system — see
docs/booking-lifecycle.md. Field-level format validation (ranges, known
enum values, string lengths) lives here; cross-field business validation
that needs the booking's current stored state (e.g. budget_max vs. an
already-stored budget_min on a partial update) lives in
app/services/booking.py, which schemas can't see.
"""

import re
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.enums import BookingEventType, BookingLocationType

_VALID_EVENT_TYPES = {member.value for member in BookingEventType}
_VALID_LOCATION_TYPES = {member.value for member in BookingLocationType}
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _validate_event_type(value: str | None) -> str | None:
    if value is not None and value not in _VALID_EVENT_TYPES:
        raise ValueError(f"event_type must be one of: {', '.join(sorted(_VALID_EVENT_TYPES))}")
    return value


def _validate_location_type(value: str | None) -> str | None:
    if value is not None and value not in _VALID_LOCATION_TYPES:
        raise ValueError(
            f"location_type must be one of: {', '.join(sorted(_VALID_LOCATION_TYPES))}"
        )
    return value


def _validate_currency(value: str) -> str:
    upper = value.strip().upper()
    if not _CURRENCY_RE.match(upper):
        raise ValueError("currency must be a 3-letter ISO 4217 code (e.g. INR, USD).")
    return upper


class BookingDraftCreateRequest(BaseModel):
    artist_profile_id: uuid.UUID


class BookingDraftUpdateRequest(BaseModel):
    """All fields optional/partial — see
    app/services/booking.py::DRAFT_EDITABLE_FIELDS. Only the fields actually
    present in the request body (`exclude_unset`) are applied."""

    service_id: uuid.UUID | None = None
    design_id: uuid.UUID | None = None
    requested_date: date | None = None
    requested_time: time | None = None
    location_type: str | None = None
    location_address: str | None = Field(default=None, max_length=2000)
    event_type: str | None = None
    num_customers: int | None = Field(default=None, gt=0)
    design_preferences: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    contact_name: str | None = Field(default=None, max_length=150)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=30)

    @field_validator("location_type")
    @classmethod
    def _check_location_type(cls, value: str | None) -> str | None:
        return _validate_location_type(value)

    @field_validator("event_type")
    @classmethod
    def _check_event_type(cls, value: str | None) -> str | None:
        return _validate_event_type(value)


class QuoteCreateRequest(BaseModel):
    """Also used for "quote revision" — see app/services/booking.py::send_quote."""

    amount: float = Field(gt=0)
    currency: str
    terms: str | None = Field(default=None, max_length=3000)
    valid_until: datetime | None = None

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, value: str) -> str:
        return _validate_currency(value)


class QuoteRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CancelBookingRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RescheduleRequest(BaseModel):
    new_date: date
    new_time: time | None = None
    reason: str | None = Field(default=None, max_length=500)


class BookingQuoteOut(BaseModel):
    id: uuid.UUID
    amount: float
    currency: str
    terms: str | None
    valid_until: datetime | None
    status: str
    created_at: datetime


class BookingStatusHistoryOut(BaseModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    changed_by: uuid.UUID | None
    reason: str | None
    created_at: datetime


class BookingAttachmentOut(BaseModel):
    id: uuid.UUID
    file_url: str
    file_type: str
    caption: str | None
    uploaded_by: uuid.UUID
    created_at: datetime


class BookingSummaryOut(BaseModel):
    id: uuid.UUID
    artist_profile_id: uuid.UUID
    artist_display_name: str | None
    customer_id: uuid.UUID
    customer_display_name: str | None
    service_id: uuid.UUID | None
    service_name: str | None
    status: str
    requested_date: date | None
    requested_time: time | None
    location_type: str | None
    event_type: str | None
    num_customers: int | None
    total_amount: float | None
    currency: str
    created_at: datetime
    updated_at: datetime


class BookingDetailOut(BookingSummaryOut):
    design_id: uuid.UUID | None
    location_address: str | None
    design_preferences: str | None
    notes: str | None
    budget_min: float | None
    budget_max: float | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    deposit_amount: float | None
    cancelled_by: uuid.UUID | None
    cancellation_reason: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    quotes: list[BookingQuoteOut]
    status_history: list[BookingStatusHistoryOut]
    attachments: list[BookingAttachmentOut]


class BookingImageUploadResponse(BaseModel):
    attachment: BookingAttachmentOut
