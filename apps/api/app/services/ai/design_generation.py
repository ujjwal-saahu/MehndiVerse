"""Personalized AI design generation — see docs/ai-design-assistant.md.

The structured form (style/occasion/body_placement/difficulty_level/
density/is_symmetric/pattern_elements/theme/personalization_text/
additional_instructions) is validated and turned into one plain-English
prompt (`build_prompt`), which is what actually gets sent to the provider —
never the raw form fields. Generation happens through the same job queue
every other Phase 20 capability uses (`app/services/ai/jobs.py`); nothing
here ever calls a provider synchronously from a route.

Every generated image is run back through the provider's own
`moderate_image` — the same moderation hook Phase 20 built for catalog
images — before it's ever shareable, satisfying "moderate prompts and
outputs" from both ends: `moderate_form_text` gates the prompt before a job
is even enqueued, `process_job` moderates the pixels the provider actually
produced.
"""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import (
    AiGenerationStatus,
    AiGenerationType,
    AiReviewStatus,
    AnalyticsEventType,
    UsageType,
)
from app.db.models.ai import AiDesignRequest, AiGeneration, AiJob
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.user import User
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError
from app.services.analytics.events import record_event
from app.services.entitlements import check_and_increment_usage
from app.services.messaging import get_or_create_booking_conversation, send_message

from .factory import get_ai_provider
from .jobs import enqueue_job, register_handler

RESULT_BUCKET = "ai-generated-designs"
JOB_TYPE = "design_generation"

# See docs/ai-design-assistant.md#ai-generated-label — every response
# schema that surfaces a generated design includes this verbatim, and
# `send_to_artist`'s message body includes it too, so the label travels
# with the content wherever it goes, not just in one API response shape.
AI_GENERATED_LABEL = "AI-generated design — not created by a human artist."

VIEW_URL_TTL_SECONDS = 600
SHARE_URL_TTL_SECONDS = 3600

MAX_STYLE_LENGTH = 100
MAX_THEME_LENGTH = 100
MAX_PERSONALIZATION_LENGTH = 50
MAX_ADDITIONAL_INSTRUCTIONS_LENGTH = 500
MAX_PATTERN_ELEMENTS = 10
MAX_PATTERN_ELEMENT_LENGTH = 40

# A deliberately small, foundation-level keyword blocklist for the *prompt*
# side of "moderate prompts and outputs" — see docs/ai-design-assistant.md
# #moderate-prompts-and-outputs. Real content-safety classification needs a
# trained model; this catches the most obviously disallowed requests
# without one, the same "heuristic foundation, not a classifier" precedent
# `app/services/ai/local_provider.py` already sets for image moderation.
# Deliberately not configurable via `SystemSetting` (unlike the Phase 20
# feature flags) — this is a hard safety floor, not a product toggle.
_BLOCKED_PROMPT_KEYWORDS = (
    "nude",
    "naked",
    "nsfw",
    "porn",
    "sex",
    "gore",
    "kill",
    "suicide",
    "self-harm",
    "hate",
    "nazi",
    "terrorist",
    "weapon",
    "bomb",
    "explicit",
)


def _blocked_keyword_in(text: str) -> str | None:
    lowered = text.lower()
    for keyword in _BLOCKED_PROMPT_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def moderate_form_text(
    *,
    style: str,
    theme: str | None,
    personalization_text: str | None,
    additional_instructions: str | None,
    pattern_elements: list[str],
) -> None:
    """Raises `AppError(422)` if any free-text field contains obviously
    disallowed content. Runs before quota is charged and before any job is
    enqueued — rejecting early means a disallowed prompt never costs the
    user a generation credit and never reaches a provider."""
    candidates = [style, theme, personalization_text, additional_instructions, *pattern_elements]
    for value in candidates:
        if not value:
            continue
        if _blocked_keyword_in(value) is not None:
            raise AppError(
                "Your request includes content we can't generate. Please rephrase and try again.",
                status_code=422,
            )


def build_prompt(
    *,
    style: str,
    occasion: str,
    body_placement: str,
    difficulty_level: str,
    density: str,
    is_symmetric: bool,
    pattern_elements: list[str],
    theme: str | None,
    personalization_text: str | None,
    additional_instructions: str | None,
) -> str:
    """Deterministic prompt construction — see docs/ai-design-assistant.md
    #prompt-construction. Every structured field is folded into one plain-
    English instruction a text-to-image provider can consume; nothing here
    is left for the provider to guess."""
    sentences = [
        f"A {density} {style} mehndi (henna) design for a {occasion.replace('_', ' ')}, "
        f"intended for the {body_placement}, at {difficulty_level} difficulty.",
        "Symmetric layout." if is_symmetric else "Asymmetric, freeform layout.",
    ]
    if pattern_elements:
        sentences.append(f"Include these pattern elements: {', '.join(pattern_elements)}.")
    if theme:
        sentences.append(f"Theme: {theme}.")
    if personalization_text:
        sentences.append(
            f"Tastefully incorporate the following initials or text into the design: "
            f'"{personalization_text}".'
        )
    if additional_instructions:
        sentences.append(additional_instructions)
    sentences.append(
        "Traditional henna line-art style, brown henna paste on skin, no text overlays, "
        "no watermarks."
    )
    return " ".join(sentences)


def create_design_request(
    db: Session,
    *,
    user: User,
    style: str,
    occasion: str,
    body_placement: str,
    difficulty_level: str,
    density: str,
    is_symmetric: bool,
    pattern_elements: list[str],
    theme: str | None,
    personalization_text: str | None,
    additional_instructions: str | None,
    allow_provider_training: bool,
) -> AiDesignRequest:
    moderate_form_text(
        style=style,
        theme=theme,
        personalization_text=personalization_text,
        additional_instructions=additional_instructions,
        pattern_elements=pattern_elements,
    )

    prompt = build_prompt(
        style=style,
        occasion=occasion,
        body_placement=body_placement,
        difficulty_level=difficulty_level,
        density=density,
        is_symmetric=is_symmetric,
        pattern_elements=pattern_elements,
        theme=theme,
        personalization_text=personalization_text,
        additional_instructions=additional_instructions,
    )

    # Must run in the same transaction as everything below — a later
    # rollback undoes the usage increment along with the request itself,
    # same invariant `check_and_increment_usage` documents.
    check_and_increment_usage(
        db, user=user, usage_type=UsageType.AI_GENERATION.value, limit_key="ai_credits_per_month"
    )

    generation = AiGeneration(
        user_id=user.id,
        generation_type=AiGenerationType.GENERATIVE_DESIGN.value,
        request_payload={
            "prompt": prompt,
            "style": style,
            "occasion": occasion,
            "body_placement": body_placement,
            "difficulty_level": difficulty_level,
            "density": density,
            "is_symmetric": is_symmetric,
            "pattern_elements": pattern_elements,
            "theme": theme,
            "personalization_text": personalization_text,
            "additional_instructions": additional_instructions,
        },
    )
    db.add(generation)
    db.flush()

    request = AiDesignRequest(
        user_id=user.id,
        generation_id=generation.id,
        style=style,
        occasion=occasion,
        body_placement=body_placement,
        difficulty_level=difficulty_level,
        density=density,
        is_symmetric=is_symmetric,
        pattern_elements=pattern_elements,
        theme=theme,
        personalization_text=personalization_text,
        additional_instructions=additional_instructions,
        allow_provider_training=allow_provider_training,
        prompt=prompt,
        max_retries=get_settings().ai_design_request_max_retries,
    )
    db.add(request)
    db.flush()

    enqueue_job(
        db,
        generation=generation,
        job_type=JOB_TYPE,
        payload={"request_id": str(request.id)},
    )
    record_event(
        db,
        event_type=AnalyticsEventType.AI_GENERATION_REQUESTED.value,
        user_id=user.id,
        entity_type="ai_design_request",
        entity_id=request.id,
        properties={"style": style, "occasion": occasion},
    )
    return request


def _best_effort_delete(path: str) -> None:
    try:
        supabase_storage.delete_object(bucket=RESULT_BUCKET, path=path)
    except SupabaseStorageError:
        # The database row is the source of truth for "this result is
        # gone" — a storage cleanup failure shouldn't block that (mirrors
        # app/services/previews.py::_best_effort_delete).
        pass


def process_job(db: Session, job: AiJob) -> dict[str, Any] | None:
    request_id = uuid.UUID(job.payload["request_id"])
    request = db.get(AiDesignRequest, request_id)
    if request is None or request.deleted_at is not None:
        raise ValueError(f"AI design request {request_id} no longer exists.")

    settings = get_settings()
    provider = get_ai_provider()

    started_at = time.monotonic()
    result = provider.generate_design_image(
        prompt=request.prompt, allow_training=request.allow_provider_training
    )
    latency_ms = int((time.monotonic() - started_at) * 1000)

    moderation = provider.moderate_image(image_bytes=result.image_bytes)

    extension = "png" if result.content_type == "image/png" else "jpg"
    path = f"{request.user_id}/{request.id}/result_{request.retry_count}.{extension}"
    supabase_storage.upload_private_object(
        bucket=RESULT_BUCKET, path=path, data=result.image_bytes, content_type=result.content_type
    )

    old_path = request.result_storage_path
    request.result_storage_path = path
    request.is_ai_generated = True
    db.add(request)
    if old_path is not None and old_path != path:
        _best_effort_delete(old_path)

    is_uncertain = moderation.confidence < settings.ai_moderation_review_confidence_threshold
    needs_review = moderation.is_flagged or is_uncertain

    generation = db.get(AiGeneration, job.generation_id)
    if generation is not None:
        generation.provider = result.provider
        generation.model_name = result.model
        generation.cost_usd = result.cost_usd
        generation.latency_ms = latency_ms
        generation.confidence = moderation.confidence
        generation.requires_human_review = needs_review
        generation.review_status = (
            AiReviewStatus.PENDING.value if needs_review else AiReviewStatus.NOT_REQUIRED.value
        )
        db.add(generation)

    return {
        "width": result.width,
        "height": result.height,
        "is_flagged": moderation.is_flagged,
        "cost_usd": result.cost_usd,
    }


register_handler(JOB_TYPE, process_job)


def get_design_request_or_404(db: Session, request_id: uuid.UUID) -> AiDesignRequest:
    request = db.get(AiDesignRequest, request_id)
    if request is None or request.deleted_at is not None:
        raise AppError("AI design request not found.", status_code=404)
    return request


def require_owner(request: AiDesignRequest, *, user_id: uuid.UUID) -> None:
    if request.user_id != user_id:
        raise AuthorizationError("You do not have access to this AI design request.")


def require_viewable(db: Session, request: AiDesignRequest, *, viewer: User) -> None:
    """The owner may always view their own request; the artist on the
    booking it was shared with (see `send_to_artist`) may view it too.
    Mirrors `app/services/previews.py::require_viewable` exactly."""
    if request.user_id == viewer.id:
        return
    if request.shared_with_booking_id is not None:
        booking = db.get(Booking, request.shared_with_booking_id)
        if booking is not None:
            artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
            if artist_profile is not None and artist_profile.user_id == viewer.id:
                return
    raise AuthorizationError("You do not have access to this AI design request.")


def retry_design_request(db: Session, request: AiDesignRequest, *, user: User) -> AiDesignRequest:
    """See docs/ai-design-assistant.md#generation-failure-and-retry-flow.
    Only a `failed` generation may be retried, and only up to
    `max_retries` times — both checks exist specifically to "prevent
    unlimited retries". Each retry is a genuine new provider call, so it
    consumes a fresh quota credit exactly like the original request did."""
    generation = db.get(AiGeneration, request.generation_id)
    assert generation is not None
    if generation.status != AiGenerationStatus.FAILED.value:
        raise AppError("Only a failed generation request can be retried.", status_code=422)
    if request.retry_count >= request.max_retries:
        raise AppError(
            f"You've used all {request.max_retries} retries for this design request. "
            "Start a new request instead.",
            status_code=429,
        )

    check_and_increment_usage(
        db, user=user, usage_type=UsageType.AI_GENERATION.value, limit_key="ai_credits_per_month"
    )

    request.retry_count += 1
    db.add(request)

    generation.status = AiGenerationStatus.PENDING.value
    generation.error_message = None
    generation.attempt_count = 0
    db.add(generation)

    enqueue_job(
        db,
        generation=generation,
        job_type=JOB_TYPE,
        payload={"request_id": str(request.id)},
    )
    return request


def save_design_request(db: Session, request: AiDesignRequest) -> None:
    request.is_saved = True
    request.saved_at = datetime.now(UTC)
    db.add(request)


def unsave_design_request(db: Session, request: AiDesignRequest) -> None:
    request.is_saved = False
    request.saved_at = None
    db.add(request)


def get_signed_result_url(
    request: AiDesignRequest, *, expires_in_seconds: int = VIEW_URL_TTL_SECONDS
) -> str | None:
    if request.result_storage_path is None:
        return None
    return supabase_storage.create_signed_url(
        bucket=RESULT_BUCKET,
        path=request.result_storage_path,
        expires_in_seconds=expires_in_seconds,
    )


def share_design_request(request: AiDesignRequest) -> tuple[str, int]:
    if request.result_storage_path is None:
        raise AppError("This design isn't ready to share yet.", status_code=422)
    url = supabase_storage.create_signed_url(
        bucket=RESULT_BUCKET,
        path=request.result_storage_path,
        expires_in_seconds=SHARE_URL_TTL_SECONDS,
    )
    return url, SHARE_URL_TTL_SECONDS


def send_design_request_to_artist(
    db: Session, request: AiDesignRequest, *, sender: User, booking: Booking
) -> None:
    if booking.customer_id != sender.id:
        raise AuthorizationError("You do not have access to this booking.")
    if request.result_storage_path is None:
        raise AppError("This design isn't ready to share yet.", status_code=422)

    generation = db.get(AiGeneration, request.generation_id)
    if generation is not None and generation.review_status == AiReviewStatus.REJECTED.value:
        raise AppError(
            "This design didn't pass review and can't be sent to an artist.", status_code=422
        )

    conversation = get_or_create_booking_conversation(db, booking)
    request.shared_with_booking_id = booking.id
    db.add(request)

    send_message(
        db,
        conversation,
        sender_id=sender.id,
        body=(
            f"Shared a personalized mehndi design — open your AI designs to view it. "
            f"{AI_GENERATED_LABEL}"
        ),
        attachment_url=None,
    )
    db.flush()


def delete_design_request(db: Session, request: AiDesignRequest) -> None:
    request.deleted_at = datetime.now(UTC)
    db.add(request)
    if request.result_storage_path is not None:
        _best_effort_delete(request.result_storage_path)
    db.flush()
