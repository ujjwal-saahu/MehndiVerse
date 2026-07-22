"""Duplicate-image detection — see docs/ai-foundation.md#duplicate-image-
detection.

Compares one design's `DesignEmbedding` against every other design's via
`cosine_similarity` (an O(n) scan — see docs/ai-foundation.md#similarity-
search-is-a-foundation for the indexing note this shares with
`similarity.py`). A pair scoring at or above `ai_duplicate_similarity_
threshold` is upserted as a `DesignDuplicateMatch` and flags the triggering
`AiGeneration` for human review — nothing is ever auto-removed or
auto-flagged as a policy violation; a human confirms or dismisses every
match (see docs/ai-foundation.md#human-review).
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import AiGenerationType, AiReviewStatus
from app.db.models.ai import AiGeneration, AiJob, DesignDuplicateMatch, DesignEmbedding

from .jobs import enqueue_design_ai_job, register_handler
from .local_provider import cosine_similarity

JOB_TYPE = "duplicate_detection"


def enqueue_duplicate_detection(
    db: Session, *, design_id: uuid.UUID, triggered_by: uuid.UUID | None = None
) -> AiGeneration:
    return enqueue_design_ai_job(
        db,
        design_id=design_id,
        generation_type=AiGenerationType.DUPLICATE_DETECTION.value,
        job_type=JOB_TYPE,
        triggered_by=triggered_by,
    )


def process_job(db: Session, job: AiJob) -> dict[str, Any] | None:
    design_id = uuid.UUID(job.payload["design_id"])
    source = db.execute(
        select(DesignEmbedding).where(DesignEmbedding.design_id == design_id)
    ).scalar_one_or_none()
    if source is None:
        raise ValueError(f"Design {design_id} has no embedding yet; cannot compare.")

    threshold = get_settings().ai_duplicate_similarity_threshold
    source_vector = tuple(source.embedding)

    candidates = (
        db.execute(select(DesignEmbedding).where(DesignEmbedding.design_id != design_id))
        .scalars()
        .all()
    )

    matches: list[tuple[uuid.UUID, float]] = []
    for candidate in candidates:
        if candidate.dimension != source.dimension:
            continue
        similarity = cosine_similarity(source_vector, tuple(candidate.embedding))
        if similarity >= threshold:
            matches.append((candidate.design_id, similarity))

    for matched_design_id, similarity in matches:
        existing = db.execute(
            select(DesignDuplicateMatch).where(
                DesignDuplicateMatch.design_id == design_id,
                DesignDuplicateMatch.matched_design_id == matched_design_id,
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = DesignDuplicateMatch(
                design_id=design_id, matched_design_id=matched_design_id
            )
            db.add(existing)
        existing.similarity = similarity
        db.flush()

    generation = db.get(AiGeneration, job.generation_id)
    if generation is not None and matches:
        generation.requires_human_review = True
        generation.review_status = AiReviewStatus.PENDING.value
        generation.confidence = max(similarity for _, similarity in matches)
        db.add(generation)

    return {"match_count": len(matches)}


register_handler(JOB_TYPE, process_job)
