from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.design import DesignSummaryOut, PageInfo


class LikeStatusOut(BaseModel):
    liked: bool
    like_count: int


class SaveStatusOut(BaseModel):
    saved: bool
    save_count: int


class CollectionOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_default: bool
    is_private: bool
    is_owner: bool
    cover_image_url: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime


class CollectionListOut(BaseModel):
    items: list[CollectionOut]
    page_info: PageInfo


class CollectionItemsOut(BaseModel):
    items: list[DesignSummaryOut]
    page_info: PageInfo


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_private: bool = True


class CollectionUpdateRequest(BaseModel):
    """Partial update — only fields explicitly present in the request body
    are applied (see `exclude_unset` usage in app/api/routes/collections.py).
    Sending `cover_design_id: null` explicitly clears the cover pick."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_private: bool | None = None
    cover_design_id: UUID | None = None


class CollectionItemAddRequest(BaseModel):
    design_id: UUID


class CollectionItemsReorderRequest(BaseModel):
    design_ids: list[UUID] = Field(min_length=1)
