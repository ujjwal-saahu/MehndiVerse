"""AI foundation routes — see docs/ai-foundation.md.

Two routers: `router` (`/ai/...`) for the original quota-gated freeform
generation endpoint plus generation-status polling, and `design_ai_router`
(`/designs/{design_id}/ai/...`, mirroring `app/api/routes/payments.py`'s
`/bookings/{booking_id}/payments` path-scoped-router precedent) for the
design-scoped capabilities: tag suggestions, embedding/duplicate
regeneration, moderation checks, and similar-design search.

Every capability that enqueues a job checks `is_feature_enabled` first and
returns 503 if the operator has turned it off (see
docs/ai-foundation.md#feature-flags) — this is the one place all five
job-backed capabilities share that check, so a flag flip takes effect
immediately without touching the job-queue code itself.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import DesignStatus
from app.db.models.ai import AiGeneration, DesignTagSuggestion
from app.db.models.artist import ArtistProfile
from app.db.models.design import Design
from app.db.session import get_db_session
from app.schemas.ai import (
    AiGenerationOut,
    AiGenerationRequest,
    AiGenerationStatusOut,
    SimilarDesignOut,
    TagSuggestionOut,
    TagSuggestionResolutionRequest,
)
from app.services.ai.embeddings import enqueue_embedding_generation
from app.services.ai.flags import is_feature_enabled
from app.services.ai.generations import create_ai_generation
from app.services.ai.moderation import enqueue_moderation_check
from app.services.ai.review import resolve_tag_suggestion
from app.services.ai.similarity import find_similar_designs
from app.services.ai.tagging import enqueue_tag_suggestion
from app.services.design_summaries import summaries_for_designs

router = APIRouter(prefix="/ai", tags=["ai"])
design_ai_router = APIRouter(prefix="/designs/{design_id}/ai", tags=["ai"])

_STAFF_ROLES = {"moderator", "admin", "super_admin"}


def _rate_limit() -> str:
    return get_settings().ai_rate_limit


def _get_design_or_404(db: Session, design_id: uuid.UUID) -> Design:
    design = db.get(Design, design_id)
    if design is None or design.deleted_at is not None:
        raise AppError("Design not found.", status_code=404)
    return design


def _is_owner(db: Session, design: Design, current: AuthenticatedUser) -> bool:
    if design.artist_profile_id is None:
        return False
    artist_profile = db.get(ArtistProfile, design.artist_profile_id)
    return artist_profile is not None and artist_profile.user_id == current.user.id


def _require_manage_permission(db: Session, design: Design, current: AuthenticatedUser) -> None:
    if current.effective_role in _STAFF_ROLES or _is_owner(db, design, current):
        return
    raise AuthorizationError("You do not have access to this design's AI features.")


def _require_visible_design(
    db: Session, design_id: uuid.UUID, current: AuthenticatedUser
) -> Design:
    """Same visibility rule `app/api/routes/designs.py::get_design` enforces
    (published, or owner/staff) — reimplemented here rather than imported to
    keep this route file independently deletable, the same "small per-route-
    file helper" precedent `admin_moderation.py`/`reports.py` already
    establish for `_report_out`. Without this, an unpublished design's
    existence and near-duplicates could leak through the similarity
    endpoint even though the design itself was never made public."""
    design = _get_design_or_404(db, design_id)
    if design.status == DesignStatus.PUBLISHED.value:
        return design
    if current.effective_role in _STAFF_ROLES or _is_owner(db, design, current):
        return design
    raise AppError("Design not found.", status_code=404)


def _require_feature(db: Session, feature: str) -> None:
    if not is_feature_enabled(db, feature):
        raise AppError(f"The '{feature}' AI feature is currently disabled.", status_code=503)


def _generation_status_out(generation: AiGeneration) -> AiGenerationStatusOut:
    return AiGenerationStatusOut(
        id=generation.id,
        generation_type=generation.generation_type,
        status=generation.status,
        provider=generation.provider,
        model_name=generation.model_name,
        confidence=generation.confidence,
        requires_human_review=generation.requires_human_review,
        review_status=generation.review_status,
        error_message=generation.error_message,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )


@router.post("/generations", response_model=AiGenerationOut, status_code=201)
def create_generation(
    payload: AiGenerationRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiGenerationOut:
    generation = create_ai_generation(
        db,
        user=current.user,
        generation_type=payload.generation_type,
        request_payload=payload.request_payload,
    )
    db.commit()
    db.refresh(generation)
    return AiGenerationOut(
        id=generation.id,
        generation_type=generation.generation_type,
        status=generation.status,
        response_payload=generation.response_payload,
        created_at=generation.created_at,
    )


@router.get("/generations/{generation_id}", response_model=AiGenerationStatusOut)
def get_generation_status(
    generation_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiGenerationStatusOut:
    generation = db.get(AiGeneration, generation_id)
    if generation is None:
        raise AppError("AI generation not found.", status_code=404)
    is_staff = current.effective_role in _STAFF_ROLES
    if generation.user_id != current.user.id and not is_staff:
        raise AuthorizationError("You do not have access to this AI generation.")
    return _generation_status_out(generation)


@design_ai_router.post("/tag-suggestions", response_model=AiGenerationStatusOut, status_code=202)
@limiter.limit(_rate_limit())
def request_tag_suggestions(
    request: Request,
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiGenerationStatusOut:
    _require_feature(db, "tag_suggestions")
    design = _get_design_or_404(db, design_id)
    _require_manage_permission(db, design, current)
    generation = enqueue_tag_suggestion(db, design=design, triggered_by=current.user.id)
    db.commit()
    db.refresh(generation)
    return _generation_status_out(generation)


@design_ai_router.get("/tag-suggestions", response_model=list[TagSuggestionOut])
def list_tag_suggestions(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TagSuggestionOut]:
    design = _get_design_or_404(db, design_id)
    _require_manage_permission(db, design, current)
    suggestions = (
        db.execute(
            select(DesignTagSuggestion)
            .where(DesignTagSuggestion.design_id == design_id)
            .order_by(DesignTagSuggestion.confidence.desc())
        )
        .scalars()
        .all()
    )
    return [
        TagSuggestionOut(
            id=s.id,
            design_id=s.design_id,
            tag_name=s.tag_name,
            confidence=s.confidence,
            status=s.status,
            created_at=s.created_at,
        )
        for s in suggestions
    ]


@design_ai_router.post("/tag-suggestions/{suggestion_id}/resolve", response_model=TagSuggestionOut)
def resolve_tag_suggestion_route(
    design_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    payload: TagSuggestionResolutionRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TagSuggestionOut:
    design = _get_design_or_404(db, design_id)
    _require_manage_permission(db, design, current)
    suggestion = db.get(DesignTagSuggestion, suggestion_id)
    if suggestion is None or suggestion.design_id != design_id:
        raise AppError("Tag suggestion not found.", status_code=404)
    resolve_tag_suggestion(db, suggestion, resolved_by=current.user.id, accepted=payload.accepted)
    db.commit()
    db.refresh(suggestion)
    return TagSuggestionOut(
        id=suggestion.id,
        design_id=suggestion.design_id,
        tag_name=suggestion.tag_name,
        confidence=suggestion.confidence,
        status=suggestion.status,
        created_at=suggestion.created_at,
    )


@design_ai_router.post("/embeddings", response_model=AiGenerationStatusOut, status_code=202)
@limiter.limit(_rate_limit())
def request_embedding_generation(
    request: Request,
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiGenerationStatusOut:
    _require_feature(db, "embeddings")
    design = _get_design_or_404(db, design_id)
    _require_manage_permission(db, design, current)
    generation = enqueue_embedding_generation(db, design=design, triggered_by=current.user.id)
    db.commit()
    db.refresh(generation)
    return _generation_status_out(generation)


@design_ai_router.post("/moderation-check", response_model=AiGenerationStatusOut, status_code=202)
@limiter.limit(_rate_limit())
def request_moderation_check(
    request: Request,
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiGenerationStatusOut:
    _require_feature(db, "moderation")
    design = _get_design_or_404(db, design_id)
    _require_manage_permission(db, design, current)
    generation = enqueue_moderation_check(db, design=design, triggered_by=current.user.id)
    db.commit()
    db.refresh(generation)
    return _generation_status_out(generation)


@design_ai_router.get("/similar", response_model=list[SimilarDesignOut])
def list_similar_designs(
    design_id: uuid.UUID,
    limit: int = 10,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SimilarDesignOut]:
    limit = max(1, min(limit, 50))
    _require_visible_design(db, design_id, current)
    scored = find_similar_designs(db, design_id=design_id, limit=limit)
    if not scored:
        return []

    # Only ever surface published designs as matches — a match landing on an
    # unpublished design (e.g. a staff-curated draft) must not leak its
    # existence to a caller who isn't its owner or staff.
    designs_by_id = {
        d.id: d
        for d in db.execute(
            select(Design).where(
                Design.id.in_([design_id_ for design_id_, _ in scored]),
                Design.deleted_at.is_(None),
                Design.status == DesignStatus.PUBLISHED.value,
            )
        )
        .scalars()
        .all()
    }
    ordered_designs = [designs_by_id[d_id] for d_id, _ in scored if d_id in designs_by_id]
    summaries = summaries_for_designs(db, ordered_designs)
    summary_by_id = {s.id: s for s in summaries}

    results: list[SimilarDesignOut] = []
    for matched_id, similarity in scored:
        summary = summary_by_id.get(matched_id)
        if summary is None:
            continue
        results.append(SimilarDesignOut(design=summary, similarity=similarity))
    return results
