"""Moderation hooks — see docs/ai-foundation.md#moderation-hooks.

Deliberately a *hook*, not an auto-moderation pipeline: `LocalHeuristicProvider
.moderate_image` can only catch broad signal-quality problems (near-blank
images, tiny thumbnails), never actual policy violations, so every flagged
result is `requires_human_review = True` and `review_status = pending` —
nothing here ever changes a `Design`'s own `status` column. A *low*-
confidence result (the provider itself is unsure) is required to route to a
human even when it isn't flagged, per this phase's "require human review for
uncertain moderation outcomes" requirement — see
`ai_moderation_review_confidence_threshold`.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import AiGenerationType, AiReviewStatus
from app.db.models.ai import AiGeneration, AiJob
from app.db.models.design import Design

from . import imaging
from .factory import get_ai_provider
from .jobs import enqueue_design_ai_job, register_handler

JOB_TYPE = "moderation_check"


def enqueue_moderation_check(
    db: Session, *, design: Design, triggered_by: uuid.UUID | None = None
) -> AiGeneration:
    return enqueue_design_ai_job(
        db,
        design_id=design.id,
        generation_type=AiGenerationType.MODERATION_CHECK.value,
        job_type=JOB_TYPE,
        triggered_by=triggered_by,
    )


def process_job(db: Session, job: AiJob) -> dict[str, Any] | None:
    design_id = uuid.UUID(job.payload["design_id"])
    image_url = imaging.get_primary_ready_image_url(db, design_id)
    if image_url is None:
        raise imaging.ImageFetchError(f"Design {design_id} has no ready primary image.")

    settings = get_settings()
    image_bytes = imaging.fetch_image_bytes(
        image_url, timeout_seconds=settings.ai_provider_timeout_seconds
    )
    provider = get_ai_provider()
    result = provider.moderate_image(image_bytes=image_bytes)

    is_uncertain = result.confidence < settings.ai_moderation_review_confidence_threshold
    needs_review = result.is_flagged or is_uncertain

    generation = db.get(AiGeneration, job.generation_id)
    if generation is not None:
        generation.provider = result.provider
        generation.model_name = result.model
        generation.confidence = result.confidence
        generation.requires_human_review = needs_review
        generation.review_status = (
            AiReviewStatus.PENDING.value if needs_review else AiReviewStatus.NOT_REQUIRED.value
        )
        db.add(generation)

    return {
        "is_flagged": result.is_flagged,
        "confidence": result.confidence,
        "categories": list(result.categories),
    }


register_handler(JOB_TYPE, process_job)
