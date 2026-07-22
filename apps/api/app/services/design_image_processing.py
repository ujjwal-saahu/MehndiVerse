"""Design image upload pipeline — steps 3-8 of docs/design-catalog.md
#image-upload-pipeline (upload original, record it, generate thumbnails,
store dimensions, mark ready).

Phase 6 has no real background worker (Celery/RQ/etc.) provisioned, so
`queue_image_processing()` runs synchronously, in-process, inside the same
request that authorized the upload. It is still a distinct, named function
boundary — swapping its body for "publish a job and return immediately" in a
later phase would not require changing anything that calls it, or the
DesignImage status contract (pending -> processing -> ready|failed).
"""

import uuid

from sqlalchemy.orm import Session

from app.core.images import ProcessedImage, generate_thumbnail
from app.db.enums import DesignImageStatus
from app.db.models.design import DesignImage
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError

THUMBNAIL_SMALL_MAX_DIMENSION = 200
THUMBNAIL_MEDIUM_MAX_DIMENSION = 800

# Design photos are marketing content for the artist's portfolio, so they
# reuse the `portfolio` Storage bucket (public read, owner write) defined in
# infrastructure/supabase/storage_policies.sql — the same bucket Phase 3
# reserved for exactly this purpose, rather than provisioning a new one.
_BUCKET = "portfolio"


def storage_prefix(*, artist_user_id: uuid.UUID, design_id: uuid.UUID, image_id: uuid.UUID) -> str:
    """`{artist_user_id}/...` is required by the bucket's RLS policy (only the
    first path segment is checked); the design/image ids beneath it just keep
    uploads organized."""
    return f"{artist_user_id}/{design_id}/{image_id}"


def queue_image_processing(
    db: Session, *, design_image: DesignImage, processed: ProcessedImage, prefix: str
) -> None:
    """Uploads the validated original plus small/medium thumbnail variants,
    then marks the row `ready`. Any storage failure marks it `failed` with a
    message instead of raising — the row is always left in a terminal,
    queryable state rather than stuck in `processing`."""
    design_image.status = DesignImageStatus.PROCESSING.value
    db.add(design_image)
    db.commit()

    try:
        image_url = supabase_storage.upload_object(
            bucket=_BUCKET,
            path=f"{prefix}/original.{processed.extension}",
            data=processed.data,
            content_type=processed.content_type,
        )
        small_bytes = generate_thumbnail(processed, max_dimension=THUMBNAIL_SMALL_MAX_DIMENSION)
        small_url = supabase_storage.upload_object(
            bucket=_BUCKET,
            path=f"{prefix}/thumb_small.{processed.extension}",
            data=small_bytes,
            content_type=processed.content_type,
        )
        medium_bytes = generate_thumbnail(processed, max_dimension=THUMBNAIL_MEDIUM_MAX_DIMENSION)
        medium_url = supabase_storage.upload_object(
            bucket=_BUCKET,
            path=f"{prefix}/thumb_medium.{processed.extension}",
            data=medium_bytes,
            content_type=processed.content_type,
        )
    except SupabaseStorageError as exc:
        design_image.status = DesignImageStatus.FAILED.value
        design_image.processing_error = str(exc)
        db.add(design_image)
        db.commit()
        return

    design_image.image_url = image_url
    design_image.thumbnail_small_url = small_url
    design_image.thumbnail_medium_url = medium_url
    design_image.status = DesignImageStatus.READY.value
    db.add(design_image)
    db.commit()
