"""Request/response models for design comments — see
docs/community-and-trust.md#1-design-comments-and-replies. Replies are
nested directly under their parent comment in `CommentOut.replies` (never
more than one level deep — see
docs/community-and-trust.md#2-comment-replies-are-flat), so a client never
needs a second round-trip to see a comment's replies.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_comment_id: uuid.UUID | None = None


class CommentUpdateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ReplyOut(BaseModel):
    id: uuid.UUID
    design_id: uuid.UUID
    user_id: uuid.UUID
    user_display_name: str | None
    parent_comment_id: uuid.UUID
    body: str
    created_at: datetime
    updated_at: datetime


class CommentOut(BaseModel):
    id: uuid.UUID
    design_id: uuid.UUID
    user_id: uuid.UUID
    user_display_name: str | None
    parent_comment_id: None = None
    body: str
    replies: list[ReplyOut]
    created_at: datetime
    updated_at: datetime


class CommentListOut(BaseModel):
    items: list[CommentOut]


class CommentEditOut(BaseModel):
    """Response shape for editing/inspecting a single comment or reply —
    unlike `CommentOut`, `parent_comment_id` reflects the row's real value
    (null for a top-level comment, set for a reply) since this isn't
    restricted to the list endpoint's "always top-level" shape."""

    id: uuid.UUID
    design_id: uuid.UUID
    user_id: uuid.UUID
    user_display_name: str | None
    parent_comment_id: uuid.UUID | None
    body: str
    created_at: datetime
    updated_at: datetime
