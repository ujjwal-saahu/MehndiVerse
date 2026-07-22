"""Request/response models for hand/foot design previews — see
docs/hand-foot-preview.md.

Compositing (drawing the design overlay onto the photo) happens entirely
client-side; the backend never rasterizes anything — `OverlayTransform` is
just the editor state a client needs to resume editing exactly where it
left off. All URLs returned here are short-lived signed URLs minted fresh
on every read (see app/integrations/supabase_storage.py::create_signed_url)
— nothing durable is ever handed to a client, matching
docs/artist-verification.md#short-lived-signed-urls.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.design import DesignSummaryOut


class OverlayTransform(BaseModel):
    """Position is a fraction (0..1) of the photo's width/height, not
    pixels, so the same transform renders correctly regardless of what
    resolution the photo is displayed at on a given device."""

    x: float = Field(default=0.5, ge=0, le=1)
    y: float = Field(default=0.5, ge=0, le=1)
    scale: float = Field(default=1.0, gt=0, le=5)
    rotation_degrees: float = Field(default=0.0, ge=-360, le=360)
    flip_horizontal: bool = False
    opacity: float = Field(default=1.0, ge=0, le=1)


class PreviewProjectOut(BaseModel):
    id: uuid.UUID
    design: DesignSummaryOut | None
    source_image_url: str
    result_image_url: str | None
    overlay_transform: OverlayTransform | None
    source_width: int | None
    source_height: int | None
    status: str
    error_message: str | None
    shared_with_booking_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ExportPreviewOut(BaseModel):
    result_image_url: str


class SharePreviewOut(BaseModel):
    url: str
    expires_in_seconds: int


class SendToArtistRequest(BaseModel):
    booking_id: uuid.UUID
