"""Fetches image bytes for AI processing — the only I/O boundary in this
package that talks to the network, kept separate from
`app/services/ai/local_provider.py`'s pure computation so provider logic
never needs network mocking in tests, only this one function does (mirrors
`app/services/payments/service.py`'s "settlement is one function, called
from two places" separation of concerns).
"""

import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import DesignImageStatus
from app.db.models.design import DesignImage

MAX_FETCH_BYTES = 20 * 1024 * 1024


class ImageFetchError(Exception):
    """Raised on a network failure, timeout, non-2xx response, or a body
    over `MAX_FETCH_BYTES` — a background job handler catches this and
    fails the job/generation with the message, never crashes the worker."""


def fetch_image_bytes(url: str, *, timeout_seconds: float) -> bytes:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url)
    except httpx.TimeoutException as exc:
        raise ImageFetchError(f"Timed out fetching image after {timeout_seconds}s.") from exc
    except httpx.HTTPError as exc:
        raise ImageFetchError(f"Failed to fetch image: {exc}") from exc

    if response.status_code >= 400:
        raise ImageFetchError(f"Image fetch returned HTTP {response.status_code}.")
    if len(response.content) > MAX_FETCH_BYTES:
        raise ImageFetchError("Image exceeds the maximum size this pipeline will process.")
    return response.content


def get_primary_ready_image_url(db: Session, design_id: uuid.UUID) -> str | None:
    """Shared by every capability that needs "the" image for a design
    (tagging, embeddings, moderation) — a single definition of "primary,
    ready image" so they can never disagree with each other or with
    `app/services/design_summaries.py::thumbnail_url`'s own selection."""
    image = (
        db.execute(
            select(DesignImage)
            .where(
                DesignImage.design_id == design_id,
                DesignImage.status == DesignImageStatus.READY.value,
            )
            .order_by(DesignImage.is_primary.desc(), DesignImage.sort_order)
        )
        .scalars()
        .first()
    )
    if image is None or image.image_url is None:
        return None
    return image.image_url
