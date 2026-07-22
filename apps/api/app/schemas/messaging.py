"""Request/response models for booking messaging — see
docs/booking-messaging.md. `ConversationSummaryOut`'s booking-context fields
deliberately mirror `BookingSummaryOut` (app/schemas/booking.py), not
`BookingDetailOut` — contact_name/email/phone never appear here. See
docs/booking-messaging.md#6-avoiding-unnecessary-contact-info-exposure.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.design import PageInfo


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str | None
    attachment_url: str | None
    message_type: str
    is_read: bool
    created_at: datetime


class MessageListOut(BaseModel):
    items: list[MessageOut]
    page_info: PageInfo


class SendMessageRequest(BaseModel):
    """Used only for the JSON (text-only) send path — the multipart path
    (with an image) reads `body` as a plain form field instead, since
    `UploadFile` and a Pydantic body can't share one request."""

    body: str = Field(min_length=1, max_length=4000)


class ConversationBookingContextOut(BaseModel):
    booking_id: uuid.UUID
    status: str
    requested_date: date | None
    service_name: str | None
    artist_profile_id: uuid.UUID


class ConversationSummaryOut(BaseModel):
    id: uuid.UUID
    booking: ConversationBookingContextOut
    other_party_display_name: str | None
    last_message_preview: str | None
    last_message_at: datetime | None
    unread_count: int


class ConversationDetailOut(BaseModel):
    id: uuid.UUID
    booking: ConversationBookingContextOut
    other_party_display_name: str | None
    my_last_read_at: datetime | None


class ReportMessageRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
