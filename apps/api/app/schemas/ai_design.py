"""Request/response models for the personalized AI design assistant — see
docs/ai-design-assistant.md.

Every enum-like form field (`body_placement`, `difficulty_level`,
`occasion`, `density`) is typed as the actual `StrEnum`, not a plain `str`
— Pydantic rejects an unrecognized value with a normal 422 before the
request ever reaches the service layer, on top of the database's own
`CHECK` constraint (belt-and-suspenders, same as every other enum-backed
column in this codebase).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.enums import BodyPlacement, BookingEventType, DesignDifficulty, PatternDensity
from app.schemas.design import PageInfo

MAX_STYLE_LENGTH = 100
MAX_THEME_LENGTH = 100
MAX_PERSONALIZATION_LENGTH = 50
MAX_ADDITIONAL_INSTRUCTIONS_LENGTH = 500
MAX_PATTERN_ELEMENTS = 10
MAX_PATTERN_ELEMENT_LENGTH = 40


class DesignGenerationRequest(BaseModel):
    """The structured form — see docs/ai-design-assistant.md#structured-
    form."""

    style: str = Field(min_length=1, max_length=MAX_STYLE_LENGTH)
    occasion: BookingEventType
    body_placement: BodyPlacement
    difficulty_level: DesignDifficulty
    density: PatternDensity
    is_symmetric: bool = True
    pattern_elements: list[str] = Field(default_factory=list, max_length=MAX_PATTERN_ELEMENTS)
    theme: str | None = Field(default=None, max_length=MAX_THEME_LENGTH)
    personalization_text: str | None = Field(default=None, max_length=MAX_PERSONALIZATION_LENGTH)
    additional_instructions: str | None = Field(
        default=None, max_length=MAX_ADDITIONAL_INSTRUCTIONS_LENGTH
    )
    # Defaults to False and must be explicitly set True by the caller — see
    # docs/ai-design-assistant.md#consent-for-provider-training. Never
    # inferred from a subscription tier or any other implicit signal.
    allow_provider_training: bool = False


class AiDesignRequestOut(BaseModel):
    id: uuid.UUID
    style: str
    occasion: str
    body_placement: str
    difficulty_level: str
    density: str
    is_symmetric: bool
    pattern_elements: list[str]
    theme: str | None
    personalization_text: str | None
    additional_instructions: str | None
    allow_provider_training: bool
    prompt: str
    status: str
    provider: str | None
    model_name: str | None
    cost_usd: float | None
    requires_human_review: bool
    review_status: str
    error_message: str | None
    result_image_url: str | None
    is_ai_generated: bool
    ai_generated_label: str
    retry_count: int
    max_retries: int
    is_saved: bool
    saved_at: datetime | None
    shared_with_booking_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class AiDesignRequestListOut(BaseModel):
    items: list[AiDesignRequestOut]
    page_info: PageInfo


class ShareDesignRequestOut(BaseModel):
    url: str
    expires_in_seconds: int


class SendDesignRequestToArtistRequest(BaseModel):
    booking_id: uuid.UUID
