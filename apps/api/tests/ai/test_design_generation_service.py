"""Service-level tests for `app/services/ai/design_generation.py` — see
docs/ai-design-assistant.md. Uses `mock_ai_provider` (a `FakeProvider` test
double, see tests/ai/conftest.py) throughout: these are the "integration
tests using a mocked provider" this phase asked for — end-to-end through
quota enforcement, prompt construction, job enqueue/claim/process, storage
upload, moderation, retry, save/share/send-to-artist, all without a single
real network call to an AI provider."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import AiGenerationStatus, AiJobStatus, AiReviewStatus
from app.db.models.ai import AiDesignRequest, AiGeneration, AiJob
from app.db.models.usage import UsageRecord
from app.services.ai import design_generation
from app.services.ai.design_generation import (
    AI_GENERATED_LABEL,
    build_prompt,
    create_design_request,
    delete_design_request,
    get_signed_result_url,
    moderate_form_text,
    require_owner,
    require_viewable,
    retry_design_request,
    save_design_request,
    send_design_request_to_artist,
    share_design_request,
    unsave_design_request,
)
from app.services.ai.jobs import claim_due_jobs
from app.services.ai.provider import DesignImageResult, ModerationResult
from tests.ai.conftest import FakeProvider, mock_design_delete, mock_design_sign, mock_design_upload
from tests.db.factories import (
    make_ai_design_request,
    make_artist_profile,
    make_booking,
    make_subscription,
    make_subscription_plan,
    make_user,
)


def _form_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "style": "Arabic",
        "occasion": "wedding",
        "body_placement": "hand",
        "difficulty_level": "intermediate",
        "density": "bold",
        "is_symmetric": True,
        "pattern_elements": ["peacock", "paisley"],
        "theme": "royal",
        "personalization_text": "R+K",
        "additional_instructions": "Leave space at the wrist for a bracelet.",
        "allow_provider_training": False,
    }
    base.update(overrides)
    return base


def _process_the_job(db: Session) -> None:
    from app.services.ai.jobs import process_due_jobs

    summary = process_due_jobs(db, limit=10)
    assert summary.claimed == 1


# --- prompt construction -----------------------------------------------------


def test_build_prompt_includes_every_structured_field() -> None:
    prompt = build_prompt(
        style="Arabic",
        occasion="wedding",
        body_placement="hand",
        difficulty_level="intermediate",
        density="bold",
        is_symmetric=True,
        pattern_elements=["peacock", "paisley"],
        theme="royal",
        personalization_text="R+K",
        additional_instructions="Leave space for a bracelet.",
    )
    assert "Arabic" in prompt
    assert "wedding" in prompt
    assert "hand" in prompt
    assert "intermediate" in prompt
    assert "bold" in prompt
    assert "Symmetric" in prompt
    assert "peacock" in prompt and "paisley" in prompt
    assert "royal" in prompt
    assert "R+K" in prompt
    assert "bracelet" in prompt


def test_build_prompt_asymmetric_layout_says_so() -> None:
    prompt = build_prompt(
        style="floral",
        occasion="party",
        body_placement="foot",
        difficulty_level="beginner",
        density="light",
        is_symmetric=False,
        pattern_elements=[],
        theme=None,
        personalization_text=None,
        additional_instructions=None,
    )
    assert "Asymmetric" in prompt


# --- prompt moderation --------------------------------------------------------


def test_moderate_form_text_rejects_blocked_keyword_in_theme() -> None:
    with pytest.raises(AppError):
        moderate_form_text(
            style="Arabic",
            theme="weapon collection",
            personalization_text=None,
            additional_instructions=None,
            pattern_elements=[],
        )


def test_moderate_form_text_rejects_blocked_keyword_in_pattern_elements() -> None:
    with pytest.raises(AppError):
        moderate_form_text(
            style="Arabic",
            theme=None,
            personalization_text=None,
            additional_instructions=None,
            pattern_elements=["nsfw content"],
        )


def test_moderate_form_text_allows_clean_input() -> None:
    moderate_form_text(
        style="Arabic",
        theme="royal",
        personalization_text="R+K",
        additional_instructions="Leave space for a bracelet.",
        pattern_elements=["peacock", "paisley"],
    )


# --- create_design_request ----------------------------------------------------


def test_create_design_request_rejects_blocked_content_before_charging_quota(
    db_session: Session,
) -> None:
    user = make_user(db_session)
    db_session.commit()

    with pytest.raises(AppError):
        create_design_request(db_session, user=user, **_form_kwargs(theme="bomb making"))

    assert (
        db_session.execute(select(UsageRecord).where(UsageRecord.user_id == user.id)).first()
        is None
    )


def test_create_design_request_enqueues_a_job_and_creates_a_generation(
    db_session: Session,
) -> None:
    user = make_user(db_session)
    db_session.commit()

    request = create_design_request(db_session, user=user, **_form_kwargs())
    db_session.commit()

    assert request.prompt
    assert request.user_id == user.id
    generation = db_session.get(AiGeneration, request.generation_id)
    assert generation is not None
    assert generation.status == AiGenerationStatus.PENDING.value

    jobs = claim_due_jobs(db_session, limit=10)
    assert len(jobs) == 1
    assert jobs[0].job_type == design_generation.JOB_TYPE
    assert jobs[0].payload == {"request_id": str(request.id)}


def test_create_design_request_is_blocked_once_quota_is_exhausted(db_session: Session) -> None:
    user = make_user(db_session)
    plan = make_subscription_plan(
        db_session, target_role="customer", features={"ai_credits_per_month": 1}
    )
    make_subscription(db_session, user=user, plan=plan, status="active")
    db_session.commit()

    create_design_request(db_session, user=user, **_form_kwargs())
    db_session.commit()

    with pytest.raises(AppError):
        create_design_request(db_session, user=user, **_form_kwargs())


# --- process_job (mocked provider) -------------------------------------------


def test_process_job_stores_result_and_marks_generation_completed(
    db_session: Session, mock_ai_provider: FakeProvider, storage_mock
) -> None:
    mock_design_upload(storage_mock)
    user = make_user(db_session)
    db_session.commit()
    request = create_design_request(db_session, user=user, **_form_kwargs())
    db_session.commit()

    _process_the_job(db_session)
    db_session.commit()

    refreshed = db_session.get(AiDesignRequest, request.id)
    assert refreshed is not None
    assert refreshed.result_storage_path is not None

    generation = db_session.get(AiGeneration, request.generation_id)
    assert generation is not None
    assert generation.status == AiGenerationStatus.COMPLETED.value
    assert generation.provider == "fake"
    assert generation.model_name == "fake-v1"
    assert generation.cost_usd is not None
    assert float(generation.cost_usd) == pytest.approx(0.02)
    assert generation.review_status == AiReviewStatus.NOT_REQUIRED.value

    # Exactly one call reached the provider, carrying the constructed prompt.
    assert len(mock_ai_provider.generate_design_image_calls) == 1
    assert mock_ai_provider.generate_design_image_calls[0]["prompt"] == request.prompt


def test_process_job_flags_a_moderated_output_for_human_review(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, storage_mock
) -> None:
    mock_design_upload(storage_mock)
    fake = FakeProvider(
        moderation_result=ModerationResult(
            provider="fake",
            model="fake-v1",
            is_flagged=True,
            confidence=0.9,
            categories=("low_variance",),
        )
    )
    monkeypatch.setattr("app.services.ai.design_generation.get_ai_provider", lambda: fake)

    user = make_user(db_session)
    db_session.commit()
    request = create_design_request(db_session, user=user, **_form_kwargs())
    db_session.commit()

    _process_the_job(db_session)
    db_session.commit()

    generation = db_session.get(AiGeneration, request.generation_id)
    assert generation is not None
    assert generation.requires_human_review is True
    assert generation.review_status == AiReviewStatus.PENDING.value


def test_process_job_failure_is_retried_with_backoff_when_attempts_remain(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeProvider(raise_on_generate=RuntimeError("provider is down"))
    monkeypatch.setattr("app.services.ai.design_generation.get_ai_provider", lambda: fake)

    user = make_user(db_session)
    db_session.commit()
    request = create_design_request(db_session, user=user, **_form_kwargs())
    db_session.commit()

    _process_the_job(db_session)
    db_session.commit()

    job = db_session.execute(
        select(AiJob).where(AiJob.generation_id == request.generation_id)
    ).scalar_one()
    assert job.status == AiJobStatus.PENDING.value  # requeued for another attempt
    assert job.attempt_count == 1
    assert job.last_error is not None and "provider is down" in job.last_error


def test_process_job_failure_terminally_fails_the_generation_once_attempts_are_exhausted(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeProvider(raise_on_generate=RuntimeError("provider is down"))
    monkeypatch.setattr("app.services.ai.design_generation.get_ai_provider", lambda: fake)

    user = make_user(db_session)
    db_session.commit()
    request = create_design_request(db_session, user=user, **_form_kwargs())
    db_session.commit()

    job = db_session.execute(
        select(AiJob).where(AiJob.generation_id == request.generation_id)
    ).scalar_one()
    job.max_attempts = 1  # force exhaustion on the very first attempt
    db_session.commit()

    _process_the_job(db_session)
    db_session.commit()

    generation = db_session.get(AiGeneration, request.generation_id)
    assert generation is not None
    assert generation.status == AiGenerationStatus.FAILED.value
    assert generation.error_message is not None and "provider is down" in generation.error_message


# --- retry --------------------------------------------------------------------


def test_retry_requires_a_failed_generation(db_session: Session) -> None:
    user = make_user(db_session)
    request = make_ai_design_request(db_session, user=user, status=AiGenerationStatus.PENDING.value)
    db_session.commit()

    with pytest.raises(AppError):
        retry_design_request(db_session, request, user=user)


def test_retry_succeeds_and_consumes_another_credit(db_session: Session) -> None:
    user = make_user(db_session)
    request = make_ai_design_request(db_session, user=user, status=AiGenerationStatus.FAILED.value)
    db_session.commit()

    retry_design_request(db_session, request, user=user)
    db_session.commit()

    assert request.retry_count == 1
    generation = db_session.get(AiGeneration, request.generation_id)
    assert generation is not None
    assert generation.status == AiGenerationStatus.PENDING.value

    usage = db_session.execute(
        select(UsageRecord).where(UsageRecord.user_id == user.id)
    ).scalar_one()
    assert usage.count == 1


def test_retry_is_blocked_once_max_retries_is_reached(db_session: Session) -> None:
    user = make_user(db_session)
    request = make_ai_design_request(
        db_session,
        user=user,
        status=AiGenerationStatus.FAILED.value,
        retry_count=3,
        max_retries=3,
    )
    db_session.commit()

    with pytest.raises(AppError):
        retry_design_request(db_session, request, user=user)


# --- save / unsave --------------------------------------------------------------


def test_save_and_unsave_design_request(db_session: Session) -> None:
    user = make_user(db_session)
    request = make_ai_design_request(db_session, user=user)
    db_session.commit()

    save_design_request(db_session, request)
    db_session.commit()
    assert request.is_saved is True
    assert request.saved_at is not None

    unsave_design_request(db_session, request)
    db_session.commit()
    assert request.is_saved is False
    assert request.saved_at is None


# --- share / send-to-artist ------------------------------------------------------


def test_share_design_request_requires_a_ready_result(db_session: Session) -> None:
    user = make_user(db_session)
    request = make_ai_design_request(db_session, user=user, result_storage_path=None)
    db_session.commit()

    with pytest.raises(AppError):
        share_design_request(request)


def test_share_design_request_returns_a_signed_url(db_session: Session, storage_mock) -> None:
    mock_design_sign(storage_mock)
    user = make_user(db_session)
    request = make_ai_design_request(
        db_session, user=user, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()

    url, expires_in = share_design_request(request)
    assert url
    assert expires_in == design_generation.SHARE_URL_TTL_SECONDS


def test_send_to_artist_rejects_a_non_owning_sender(db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(db_session, customer=owner, artist_profile=artist_profile)
    request = make_ai_design_request(
        db_session, user=owner, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()

    with pytest.raises(AuthorizationError):
        send_design_request_to_artist(db_session, request, sender=stranger, booking=booking)


def test_send_to_artist_rejects_a_rejected_result(db_session: Session) -> None:
    owner = make_user(db_session)
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(db_session, customer=owner, artist_profile=artist_profile)
    request = make_ai_design_request(
        db_session,
        user=owner,
        result_storage_path="u/req/result_0.png",
        review_status=AiReviewStatus.REJECTED.value,
        requires_human_review=True,
    )
    db_session.commit()

    with pytest.raises(AppError):
        send_design_request_to_artist(db_session, request, sender=owner, booking=booking)


def test_send_to_artist_labels_the_message_as_ai_generated(db_session: Session) -> None:
    owner = make_user(db_session)
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(
        db_session, customer=owner, artist_profile=artist_profile, status="confirmed"
    )
    request = make_ai_design_request(
        db_session, user=owner, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()

    send_design_request_to_artist(db_session, request, sender=owner, booking=booking)
    db_session.commit()

    assert request.shared_with_booking_id == booking.id

    from app.db.models.messaging import Message

    message = (
        db_session.execute(select(Message).where(Message.sender_id == owner.id)).scalars().first()
    )
    assert message is not None
    assert AI_GENERATED_LABEL in (message.body or "")


def test_require_viewable_allows_the_shared_artist(db_session: Session) -> None:
    owner = make_user(db_session)
    artist_user = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=artist_user)
    booking = make_booking(
        db_session, customer=owner, artist_profile=artist_profile, status="confirmed"
    )
    request = make_ai_design_request(
        db_session, user=owner, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()

    send_design_request_to_artist(db_session, request, sender=owner, booking=booking)
    db_session.commit()

    require_viewable(db_session, request, viewer=artist_user)  # must not raise


def test_require_viewable_rejects_a_stranger(db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner)
    db_session.commit()

    with pytest.raises(AuthorizationError):
        require_viewable(db_session, request, viewer=stranger)


def test_require_owner_rejects_a_non_owner(db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner)
    db_session.commit()

    with pytest.raises(AuthorizationError):
        require_owner(request, user_id=stranger.id)


# --- delete -----------------------------------------------------------------


def test_delete_design_request_soft_deletes(db_session: Session, storage_mock) -> None:
    mock_design_delete(storage_mock)
    user = make_user(db_session)
    request = make_ai_design_request(
        db_session, user=user, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()

    delete_design_request(db_session, request)
    db_session.commit()

    assert request.deleted_at is not None


def test_get_signed_result_url_is_none_without_a_result(db_session: Session) -> None:
    user = make_user(db_session)
    request = make_ai_design_request(db_session, user=user, result_storage_path=None)
    db_session.commit()

    assert get_signed_result_url(request) is None


def test_design_image_result_and_fake_provider_round_trip() -> None:
    # Sanity check that the FakeProvider test double satisfies the same
    # dataclass shape a real provider must — see docs/ai-design-assistant.md
    # #keep-generation-provider-replaceable.
    fake = FakeProvider(
        design_image_result=DesignImageResult(
            provider="fake",
            model="fake-v2",
            image_bytes=b"abc",
            content_type="image/png",
            width=10,
            height=10,
            cost_usd=0.5,
        )
    )
    result = fake.generate_design_image(prompt="test")
    assert result.model == "fake-v2"
    assert result.cost_usd == 0.5
