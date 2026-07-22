"""Image embedding generation — see docs/ai-foundation.md#image-embedding-
generation.

Enqueues through the job queue (never called synchronously from a route):
computing an embedding means fetching the image and running the provider
over it, both too slow to hold an API worker for. `process_job` upserts the
design's single `DesignEmbedding` row (retry-safe — `design_id` is unique,
so re-running this job for the same design just refreshes the vector) and,
on success, chains a duplicate-detection job — duplicate detection needs an
embedding to compare against, so it can only ever run after one exists.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import AiGenerationType
from app.db.models.ai import AiGeneration, AiJob, DesignEmbedding
from app.db.models.design import Design

from . import imaging
from .factory import get_ai_provider
from .jobs import enqueue_design_ai_job, register_handler

JOB_TYPE = "embedding_generation"


def enqueue_embedding_generation(
    db: Session, *, design: Design, triggered_by: uuid.UUID | None = None
) -> AiGeneration:
    return enqueue_design_ai_job(
        db,
        design_id=design.id,
        generation_type=AiGenerationType.EMBEDDING_GENERATION.value,
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
    result = provider.generate_embedding(image_bytes=image_bytes)

    existing = db.execute(
        select(DesignEmbedding).where(DesignEmbedding.design_id == design_id)
    ).scalar_one_or_none()
    if existing is None:
        existing = DesignEmbedding(design_id=design_id)
        db.add(existing)
    existing.embedding = list(result.vector)
    existing.dimension = result.dimension
    existing.provider = result.provider
    existing.model_name = result.model
    db.flush()

    generation = db.get(AiGeneration, job.generation_id)
    if generation is not None:
        generation.provider = result.provider
        generation.model_name = result.model
        db.add(generation)

    from .duplicates import enqueue_duplicate_detection

    enqueue_duplicate_detection(db, design_id=design_id, triggered_by=None)

    return {"dimension": result.dimension, "provider": result.provider, "model": result.model}


register_handler(JOB_TYPE, process_job)
