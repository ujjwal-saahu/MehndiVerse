"""Quota-gated, freeform AI generation requests — see
docs/ai-foundation.md#ai-quota-enforcement-foundation and
docs/subscriptions-and-entitlements.md#ai-credit-foundation.

This is the direct replacement for the old (Phase 18) flat
`app/services/ai.py::create_ai_generation`, kept in this package for the
`generation_type`s that aren't backed by a specific job handler in this
phase (`design_discovery`, `photo_preview`, `generative_design` — still
foundations themselves, logging the request without doing real provider
work). The job-backed types (`tag_suggestion`, `embedding_generation`,
`duplicate_detection`, `moderation_check`) go through their own
`enqueue_*` functions in `tagging.py`/`embeddings.py`/`duplicates.py`/
`moderation.py` instead, since those need a `Design`, not just a user and a
freeform payload.

Reuses `check_and_increment_usage` (Phase 18's entitlements/quota system)
rather than inventing a second quota mechanism — this satisfies the "AI
quota enforcement foundation" requirement without any new schema.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.db.enums import AnalyticsEventType, UsageType
from app.db.models.ai import AiGeneration
from app.db.models.user import User
from app.services.analytics.events import record_event
from app.services.entitlements import check_and_increment_usage


def create_ai_generation(
    db: Session,
    *,
    user: User,
    generation_type: str,
    request_payload: dict[str, Any],
) -> AiGeneration:
    """Must run in the same transaction the caller commits — a later
    rollback undoes the usage increment along with the generation row,
    same invariant `check_and_increment_usage` itself documents."""
    check_and_increment_usage(
        db, user=user, usage_type=UsageType.AI_GENERATION.value, limit_key="ai_credits_per_month"
    )
    generation = AiGeneration(
        user_id=user.id,
        generation_type=generation_type,
        request_payload=request_payload,
    )
    db.add(generation)
    db.flush()
    record_event(
        db,
        event_type=AnalyticsEventType.AI_GENERATION_REQUESTED.value,
        user_id=user.id,
        entity_type="ai_generation",
        entity_id=generation.id,
        properties={"generation_type": generation_type},
    )
    return generation
