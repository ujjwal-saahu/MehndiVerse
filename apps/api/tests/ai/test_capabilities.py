"""End-to-end job processing for the four provider-backed capabilities —
tagging, embeddings (+duplicate-detection chaining), moderation. Each test
enqueues through the capability's own `enqueue_*`, then runs `process_job`
directly against the row `claim_due_jobs` would have handed a worker,
mirroring exactly what `app/services/ai/jobs.py::process_due_jobs` does.
"""

import io

import httpx
import respx
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import AiReviewStatus, TagSuggestionStatus
from app.db.models.ai import (
    AiGeneration,
    AiJob,
    DesignDuplicateMatch,
    DesignEmbedding,
    DesignTagSuggestion,
)
from app.services.ai import duplicates, embeddings, moderation, tagging
from app.services.ai import imaging as imaging_module
from app.services.ai.jobs import claim_due_jobs
from tests.ai.conftest import make_ready_design_image, make_test_image_bytes
from tests.db.factories import make_design, make_design_embedding


def _claim_single_job(db: Session, job_type: str) -> AiJob:
    jobs = [j for j in claim_due_jobs(db, limit=50) if j.job_type == job_type]
    assert len(jobs) == 1, f"expected exactly one due {job_type} job, found {len(jobs)}"
    return jobs[0]


def test_tag_suggestion_job_creates_suggestions_from_the_primary_image(
    db_session: Session, image_host_mock: respx.MockRouter
) -> None:
    design = make_design(db_session)
    make_ready_design_image(db_session, design=design, image_url="https://example.test/gold.png")
    image_host_mock.get("/gold.png").mock(
        return_value=httpx.Response(
            200,
            content=make_test_image_bytes(color=(212, 175, 55)),
            headers={"content-type": "image/png"},
        )
    )
    generation = tagging.enqueue_tag_suggestion(db_session, design=design)
    db_session.commit()

    job = _claim_single_job(db_session, tagging.JOB_TYPE)
    result = tagging.process_job(db_session, job)
    db_session.commit()

    assert result is not None and result["suggested_count"] > 0
    rows = (
        db_session.execute(
            select(DesignTagSuggestion).where(DesignTagSuggestion.design_id == design.id)
        )
        .scalars()
        .all()
    )
    assert len(rows) > 0
    assert all(r.status == TagSuggestionStatus.PENDING.value for r in rows)

    refreshed_generation = db_session.get(AiGeneration, generation.id)
    assert refreshed_generation is not None
    assert refreshed_generation.provider == "local"


def test_tag_suggestion_rerun_never_overwrites_a_human_decision(
    db_session: Session, image_host_mock: respx.MockRouter
) -> None:
    design = make_design(db_session)
    make_ready_design_image(db_session, design=design, image_url="https://example.test/gold2.png")
    image_host_mock.get("/gold2.png").mock(
        return_value=httpx.Response(
            200,
            content=make_test_image_bytes(color=(212, 175, 55)),
            headers={"content-type": "image/png"},
        )
    )
    tagging.enqueue_tag_suggestion(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, tagging.JOB_TYPE)
    tagging.process_job(db_session, job)
    db_session.commit()

    accepted = (
        db_session.execute(
            select(DesignTagSuggestion).where(DesignTagSuggestion.design_id == design.id)
        )
        .scalars()
        .first()
    )
    assert accepted is not None
    accepted.status = TagSuggestionStatus.ACCEPTED.value
    accepted.confidence = 0.1234
    db_session.commit()

    tagging.enqueue_tag_suggestion(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, tagging.JOB_TYPE)
    tagging.process_job(db_session, job)
    db_session.commit()

    refreshed = db_session.get(DesignTagSuggestion, accepted.id)
    assert refreshed is not None
    assert refreshed.status == TagSuggestionStatus.ACCEPTED.value
    assert refreshed.confidence == 0.1234


def test_embedding_job_upserts_embedding_and_chains_duplicate_detection(
    db_session: Session, image_host_mock: respx.MockRouter
) -> None:
    design = make_design(db_session)
    make_ready_design_image(db_session, design=design, image_url="https://example.test/embed.png")
    image_host_mock.get("/embed.png").mock(
        return_value=httpx.Response(
            200, content=make_test_image_bytes(), headers={"content-type": "image/png"}
        )
    )
    embeddings.enqueue_embedding_generation(db_session, design=design)
    db_session.commit()

    job = _claim_single_job(db_session, embeddings.JOB_TYPE)
    result = embeddings.process_job(db_session, job)
    db_session.commit()

    assert result is not None and result["dimension"] == 112
    stored = db_session.execute(
        select(DesignEmbedding).where(DesignEmbedding.design_id == design.id)
    ).scalar_one_or_none()
    assert stored is not None
    assert stored.provider == "local"

    # Success chains a duplicate-detection job for the same design.
    chained = (
        db_session.execute(select(AiJob).where(AiJob.job_type == duplicates.JOB_TYPE))
        .scalars()
        .all()
    )
    assert len(chained) == 1


def test_embedding_job_is_idempotent_on_rerun(
    db_session: Session, image_host_mock: respx.MockRouter
) -> None:
    design = make_design(db_session)
    make_ready_design_image(db_session, design=design, image_url="https://example.test/embed2.png")
    image_host_mock.get("/embed2.png").mock(
        return_value=httpx.Response(
            200, content=make_test_image_bytes(), headers={"content-type": "image/png"}
        )
    )
    embeddings.enqueue_embedding_generation(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, embeddings.JOB_TYPE)
    embeddings.process_job(db_session, job)
    db_session.commit()

    embeddings.enqueue_embedding_generation(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, embeddings.JOB_TYPE)
    embeddings.process_job(db_session, job)
    db_session.commit()

    rows = (
        db_session.execute(select(DesignEmbedding).where(DesignEmbedding.design_id == design.id))
        .scalars()
        .all()
    )
    assert len(rows) == 1


def test_duplicate_detection_flags_a_near_identical_embedding(db_session: Session) -> None:
    design_a = make_design(db_session)
    design_b = make_design(db_session)
    shared_vector = [0.9] * 8
    make_design_embedding(db_session, design=design_a, embedding=shared_vector)
    make_design_embedding(db_session, design=design_b, embedding=shared_vector)
    db_session.commit()

    generation = duplicates.enqueue_duplicate_detection(db_session, design_id=design_a.id)
    db_session.commit()
    job = _claim_single_job(db_session, duplicates.JOB_TYPE)
    result = duplicates.process_job(db_session, job)
    db_session.commit()

    assert result is not None and result["match_count"] == 1
    match = db_session.execute(
        select(DesignDuplicateMatch).where(DesignDuplicateMatch.design_id == design_a.id)
    ).scalar_one_or_none()
    assert match is not None
    assert match.matched_design_id == design_b.id

    refreshed_generation = db_session.get(AiGeneration, generation.id)
    assert refreshed_generation is not None
    assert refreshed_generation.requires_human_review is True
    assert refreshed_generation.review_status == AiReviewStatus.PENDING.value


def test_duplicate_detection_ignores_dissimilar_embeddings(db_session: Session) -> None:
    design_a = make_design(db_session)
    design_b = make_design(db_session)
    make_design_embedding(db_session, design=design_a, embedding=[1.0, 0.0, 0.0, 0.0])
    make_design_embedding(db_session, design=design_b, embedding=[0.0, 1.0, 0.0, 0.0])
    db_session.commit()

    duplicates.enqueue_duplicate_detection(db_session, design_id=design_a.id)
    db_session.commit()
    job = _claim_single_job(db_session, duplicates.JOB_TYPE)
    result = duplicates.process_job(db_session, job)
    db_session.commit()

    assert result == {"match_count": 0}
    assert (
        db_session.execute(
            select(DesignDuplicateMatch).where(DesignDuplicateMatch.design_id == design_a.id)
        ).first()
        is None
    )


def test_moderation_check_flags_a_tiny_low_variance_image(
    db_session: Session, image_host_mock: respx.MockRouter
) -> None:
    design = make_design(db_session)
    make_ready_design_image(db_session, design=design, image_url="https://example.test/tiny.png")
    image_host_mock.get("/tiny.png").mock(
        return_value=httpx.Response(
            200,
            content=make_test_image_bytes(size=(10, 10), color=(128, 128, 128)),
            headers={"content-type": "image/png"},
        )
    )
    generation = moderation.enqueue_moderation_check(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, moderation.JOB_TYPE)
    result = moderation.process_job(db_session, job)
    db_session.commit()

    assert result is not None and result["is_flagged"] is True
    refreshed = db_session.get(AiGeneration, generation.id)
    assert refreshed is not None
    assert refreshed.requires_human_review is True
    assert refreshed.review_status == AiReviewStatus.PENDING.value


def test_moderation_check_does_not_require_review_for_a_confident_clean_result(
    db_session: Session, image_host_mock: respx.MockRouter
) -> None:
    checkerboard = Image.new("RGB", (200, 200))
    pixels = checkerboard.load()
    for x in range(200):
        for y in range(200):
            pixels[x, y] = (255, 255, 255) if (x // 10 + y // 10) % 2 == 0 else (0, 0, 0)
    buffer = io.BytesIO()
    checkerboard.save(buffer, format="PNG")

    design = make_design(db_session)
    make_ready_design_image(db_session, design=design, image_url="https://example.test/checker.png")
    image_host_mock.get("/checker.png").mock(
        return_value=httpx.Response(
            200, content=buffer.getvalue(), headers={"content-type": "image/png"}
        )
    )
    generation = moderation.enqueue_moderation_check(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, moderation.JOB_TYPE)
    moderation.process_job(db_session, job)
    db_session.commit()

    refreshed = db_session.get(AiGeneration, generation.id)
    assert refreshed is not None
    assert refreshed.requires_human_review is False
    assert refreshed.review_status == AiReviewStatus.NOT_REQUIRED.value


def test_capability_job_raises_when_design_has_no_ready_image(db_session: Session) -> None:
    design = make_design(db_session)
    generation = tagging.enqueue_tag_suggestion(db_session, design=design)
    db_session.commit()
    job = _claim_single_job(db_session, tagging.JOB_TYPE)

    try:
        tagging.process_job(db_session, job)
    except imaging_module.ImageFetchError:
        pass
    else:
        raise AssertionError("Expected process_job to raise when there is no ready image.")

    assert generation.id is not None  # generation row itself was still created
