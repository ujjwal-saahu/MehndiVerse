import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.design import PageInfo

_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")
_VALID_SOCIAL_PLATFORMS = {
    "instagram",
    "facebook",
    "twitter",
    "tiktok",
    "youtube",
    "pinterest",
    "website",
}


class ArtistProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    professional_name: str | None
    business_name: str | None
    headline: str | None
    bio: str | None
    years_experience: int | None
    country: str | None
    city: str | None
    service_areas: list[str]
    languages: list[str]
    contact_email: str | None
    contact_phone: str | None
    social_links: dict[str, str]
    profile_image_url: str | None
    cover_image_url: str | None
    verification_status: str
    submitted_at: datetime | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    more_info_request: str | None
    is_editable: bool
    missing_requirements: list[str]
    created_at: datetime
    updated_at: datetime


class ArtistProfileUpdateRequest(BaseModel):
    """All fields optional — only the ones present in the request body are
    applied (`exclude_unset`, see app/api/routes/artist_onboarding.py)."""

    professional_name: str | None = Field(default=None, min_length=1, max_length=150)
    business_name: str | None = Field(default=None, max_length=150)
    headline: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=80)
    country: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    service_areas: list[str] | None = Field(default=None, max_length=20)
    languages: list[str] | None = Field(default=None, max_length=20)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=30)
    social_links: dict[str, str] | None = None

    @field_validator("country")
    @classmethod
    def _validate_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        upper = value.strip().upper()
        if not _COUNTRY_CODE_RE.match(upper):
            raise ValueError("Country must be a 2-letter ISO 3166-1 alpha-2 code (e.g. IN, US).")
        return upper

    @field_validator("service_areas", "languages")
    @classmethod
    def _clean_string_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [item.strip() for item in value if item.strip()]

    @field_validator("social_links")
    @classmethod
    def _validate_social_links(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        unknown = set(value) - _VALID_SOCIAL_PLATFORMS
        if unknown:
            raise ValueError(
                f"Unknown social platform(s): {', '.join(sorted(unknown))}. "
                f"Supported: {', '.join(sorted(_VALID_SOCIAL_PLATFORMS))}."
            )
        for platform, url in value.items():
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"{platform} link must be a full URL starting with http(s)://.")
        return value


class ArtistImageUploadResponse(BaseModel):
    image_url: str


class ArtistDocumentOut(BaseModel):
    id: UUID
    document_type: str
    original_filename: str | None
    content_type: str
    file_size_bytes: int
    status: str
    rejection_reason: str | None
    reviewed_at: datetime | None
    # Minted fresh on every response, short-lived — never a durable URL. See
    # docs/artist-verification.md#short-lived-signed-urls.
    view_url: str
    created_at: datetime


class ArtistSubmissionReadinessOut(BaseModel):
    is_ready: bool
    missing_requirements: list[str]


class AuditLogEntryOut(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_display_name: str | None
    action: str
    before_state: dict[str, object] | None
    after_state: dict[str, object] | None
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogEntryOut]
    page_info: PageInfo


class ArtistVerificationQueueItemOut(BaseModel):
    id: UUID
    user_id: UUID
    professional_name: str | None
    business_name: str | None
    verification_status: str
    submitted_at: datetime | None
    document_count: int


class ArtistVerificationQueueOut(BaseModel):
    items: list[ArtistVerificationQueueItemOut]
    page_info: PageInfo


class ArtistRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ArtistRequestMoreInfoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ArtistSuspendRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class DocumentReviewRequest(BaseModel):
    status: str
    rejection_reason: str | None = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        if value not in {"approved", "rejected"}:
            raise ValueError("status must be 'approved' or 'rejected'.")
        return value

    @model_validator(mode="after")
    def _require_reason_when_rejecting(self) -> "DocumentReviewRequest":
        if self.status == "rejected" and not (self.rejection_reason or "").strip():
            raise ValueError("rejection_reason is required when rejecting a document.")
        return self
