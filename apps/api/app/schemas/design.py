from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_VALID_CATEGORY_TYPES = {"style", "occasion", "body_part", "difficulty", "density", "region"}
_VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
_VALID_BODY_PLACEMENTS = {"hand", "foot", "arm", "back", "other"}


class CategoryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    category_type: str
    description: str | None
    parent_category_id: UUID | None
    sort_order: int
    is_active: bool


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    category_type: str
    description: str | None = Field(default=None, max_length=500)
    parent_category_id: UUID | None = None
    sort_order: int = 0

    @field_validator("category_type")
    @classmethod
    def _validate_category_type(cls, value: str) -> str:
        if value not in _VALID_CATEGORY_TYPES:
            raise ValueError(
                f"category_type must be one of: {', '.join(sorted(_VALID_CATEGORY_TYPES))}"
            )
        return value


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    is_active: bool | None = None


class DesignImageOut(BaseModel):
    id: UUID
    design_id: UUID
    status: str
    image_url: str | None
    thumbnail_small_url: str | None
    thumbnail_medium_url: str | None
    width: int | None
    height: int | None
    sort_order: int
    is_primary: bool
    processing_error: str | None


class DesignImageAuthorizeResponse(BaseModel):
    image_id: UUID
    max_file_size_bytes: int
    allowed_content_types: list[str]


class ArtistSummaryOut(BaseModel):
    """The minimal artist info a design card/detail view needs — not the
    full artist profile (services, availability, etc.), which belongs to a
    future artist-profile-browsing phase."""

    id: UUID
    display_name: str
    avatar_url: str | None
    headline: str | None
    rating_average: float
    rating_count: int
    is_accepting_bookings: bool


class DesignOut(BaseModel):
    id: UUID
    artist_profile_id: UUID | None
    artist: ArtistSummaryOut | None
    title: str
    description: str | None
    difficulty_level: str | None
    body_placement: str | None
    status: str
    is_featured: bool
    is_premium: bool
    # True when this is a premium design and the viewer lacks premium
    # access — see docs/subscriptions-and-entitlements.md#premium-design-
    # access. When true, `images[].image_url`/`thumbnail_medium_url` are
    # withheld (only `thumbnail_small_url` is populated); full images
    # require a premium subscription and, separately, an available
    # download-quota unit via `POST /designs/{id}/download`.
    premium_locked: bool
    view_count: int
    like_count: int
    save_count: int
    is_liked: bool
    is_saved: bool
    categories: list[CategoryOut]
    tags: list[str]
    images: list[DesignImageOut]
    created_at: datetime
    updated_at: datetime


class DesignDownloadOut(BaseModel):
    design_id: UUID
    image_url: str


class DesignSummaryOut(BaseModel):
    """Grid-card shape — deliberately lighter than `DesignOut`: one
    thumbnail (never the full-resolution original), no description/tags/
    full image list. See docs/design-gallery.md#thumbnail-selection."""

    id: UUID
    artist_profile_id: UUID | None
    artist_display_name: str | None
    title: str
    status: str
    is_featured: bool
    is_premium: bool
    difficulty_level: str | None
    body_placement: str | None
    thumbnail_url: str | None
    view_count: int
    like_count: int
    save_count: int
    created_at: datetime


class PageInfo(BaseModel):
    next_cursor: str | None
    has_more: bool


class DesignListOut(BaseModel):
    items: list[DesignSummaryOut]
    page_info: PageInfo


class HomeFeedOut(BaseModel):
    latest: list[DesignSummaryOut]
    featured: list[DesignSummaryOut]
    trending: list[DesignSummaryOut]


class DesignCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    difficulty_level: str | None = None
    body_placement: str | None = None
    is_premium: bool = False
    category_ids: list[UUID] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)

    @field_validator("difficulty_level")
    @classmethod
    def _validate_difficulty(cls, value: str | None) -> str | None:
        if value is not None and value not in _VALID_DIFFICULTIES:
            raise ValueError(
                f"difficulty_level must be one of: {', '.join(sorted(_VALID_DIFFICULTIES))}"
            )
        return value

    @field_validator("body_placement")
    @classmethod
    def _validate_body_placement(cls, value: str | None) -> str | None:
        if value is not None and value not in _VALID_BODY_PLACEMENTS:
            raise ValueError(
                f"body_placement must be one of: {', '.join(sorted(_VALID_BODY_PLACEMENTS))}"
            )
        return value

    @field_validator("tag_names")
    @classmethod
    def _normalize_tag_names(cls, value: list[str]) -> list[str]:
        return [tag.strip().lower() for tag in value if tag.strip()]


class DesignUpdateRequest(BaseModel):
    """Partial update — only fields explicitly present in the request body
    are applied (see `exclude_unset` usage in app/api/routes/designs.py).
    `status` here only accepts the owner-facing draft<->published toggle;
    archiving and moderation flags go through their own endpoints."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    difficulty_level: str | None = None
    body_placement: str | None = None
    status: str | None = None
    is_premium: bool | None = None
    category_ids: list[UUID] | None = None
    tag_names: list[str] | None = None

    @field_validator("difficulty_level")
    @classmethod
    def _validate_difficulty(cls, value: str | None) -> str | None:
        if value is not None and value not in _VALID_DIFFICULTIES:
            raise ValueError(
                f"difficulty_level must be one of: {', '.join(sorted(_VALID_DIFFICULTIES))}"
            )
        return value

    @field_validator("body_placement")
    @classmethod
    def _validate_body_placement(cls, value: str | None) -> str | None:
        if value is not None and value not in _VALID_BODY_PLACEMENTS:
            raise ValueError(
                f"body_placement must be one of: {', '.join(sorted(_VALID_BODY_PLACEMENTS))}"
            )
        return value

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"draft", "published"}:
            raise ValueError("status must be 'draft' or 'published' via this endpoint.")
        return value

    @field_validator("tag_names")
    @classmethod
    def _normalize_tag_names(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [tag.strip().lower() for tag in value if tag.strip()]
