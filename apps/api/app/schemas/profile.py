import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")
_LOCALE_RE = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")


class ProfileOut(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: str | None
    bio: str | None
    city: str | None
    country: str | None
    locale: str | None
    timezone: str | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """All fields optional — only the ones actually present in the request
    body are applied (see `exclude_unset` usage in app/api/routes/profile.py),
    so this is a true partial update, not a full replace."""

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=2)
    locale: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("display_name", "bio", "city", "timezone")
    @classmethod
    def _strip_and_reject_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("This field cannot be blank.")
        return stripped

    @field_validator("country")
    @classmethod
    def _validate_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        upper = value.strip().upper()
        if not _COUNTRY_CODE_RE.match(upper):
            raise ValueError("Country must be a 2-letter ISO 3166-1 alpha-2 code (e.g. IN, US).")
        return upper

    @field_validator("locale")
    @classmethod
    def _validate_locale(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not _LOCALE_RE.match(stripped):
            raise ValueError("Locale must look like 'en' or 'en-US'.")
        return stripped


class AvatarUploadResponse(BaseModel):
    avatar_url: str


class UserPreferencesOut(BaseModel):
    email_notifications: bool
    push_notifications: bool
    sms_notifications: bool
    marketing_opt_in: bool
    profile_visibility: str
    show_location: bool
    allow_messages_from_strangers: bool
    analytics_consent: bool


class UserPreferencesUpdateRequest(BaseModel):
    email_notifications: bool | None = None
    push_notifications: bool | None = None
    sms_notifications: bool | None = None
    marketing_opt_in: bool | None = None
    profile_visibility: str | None = None
    show_location: bool | None = None
    allow_messages_from_strangers: bool | None = None
    analytics_consent: bool | None = None

    @field_validator("profile_visibility")
    @classmethod
    def _validate_visibility(cls, value: str | None) -> str | None:
        if value is not None and value not in {"public", "private"}:
            raise ValueError("profile_visibility must be 'public' or 'private'.")
        return value


class BlockUserRequest(BaseModel):
    user_id: UUID


class BlockedUserOut(BaseModel):
    user_id: UUID
    display_name: str | None
    blocked_at: datetime
