"""Request/response models for booking reviews — see
docs/community-and-trust.md#3-review-a-completed-booking."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str | None = Field(default=None, max_length=3000)


class ReviewOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    customer_display_name: str | None
    artist_profile_id: uuid.UUID
    rating: int
    body: str | None
    created_at: datetime


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    rating_average: float
    rating_count: int
