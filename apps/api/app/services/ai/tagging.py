"""Automatic design-tag suggestion — see docs/ai-foundation.md#automatic-
design-tag-suggestion.

Suggestions are never auto-applied to `design_tags`; they land in
`DesignTagSuggestion` for the owning artist or staff to accept/reject (see
`review.py` for moderation-style review — tag suggestions are resolved
directly via their own status column instead, since accepting one isn't a
"review" in the moderation sense, just a product action). Re-running this
job for the same design is retry-safe: an existing `pending` suggestion has
its confidence refreshed, but one a human already `accepted`/`rejected` is
left untouched.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import AiGenerationType, TagSuggestionStatus
from app.db.models.ai import AiGeneration, AiJob, DesignTagSuggestion
from app.db.models.design import Design, DesignTag, Tag

from . import imaging
from .factory import get_ai_provider
from .jobs import enqueue_design_ai_job, register_handler

JOB_TYPE = "tag_suggestion"


def enqueue_tag_suggestion(
    db: Session, *, design: Design, triggered_by: uuid.UUID | None = None
) -> AiGeneration:
    return enqueue_design_ai_job(
        db,
        design_id=design.id,
        generation_type=AiGenerationType.TAG_SUGGESTION.value,
        job_type=JOB_TYPE,
        triggered_by=triggered_by,
    )


def _existing_tag_names(db: Session, design_id: uuid.UUID) -> tuple[str, ...]:
    names = (
        db.execute(
            select(Tag.name)
            .join(DesignTag, DesignTag.tag_id == Tag.id)
            .where(DesignTag.design_id == design_id)
        )
        .scalars()
        .all()
    )
    return tuple(names)


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
    existing_tags = _existing_tag_names(db, design_id)
    result = provider.suggest_tags(image_bytes=image_bytes, existing_tags=existing_tags)

    for tag_name, confidence in result.tags:
        row = db.execute(
            select(DesignTagSuggestion).where(
                DesignTagSuggestion.design_id == design_id,
                DesignTagSuggestion.tag_name == tag_name,
            )
        ).scalar_one_or_none()
        if row is None:
            db.add(
                DesignTagSuggestion(design_id=design_id, tag_name=tag_name, confidence=confidence)
            )
        elif row.status == TagSuggestionStatus.PENDING.value:
            row.confidence = confidence
        db.flush()

    generation = db.get(AiGeneration, job.generation_id)
    if generation is not None:
        generation.provider = result.provider
        generation.model_name = result.model
        db.add(generation)

    return {"suggested_count": len(result.tags)}


register_handler(JOB_TYPE, process_job)
