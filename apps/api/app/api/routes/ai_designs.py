"""Personalized AI design assistant routes — see docs/ai-design-assistant.md.

Every write here is scoped to the request's owner (`require_owner`) except
`GET /ai/designs/{id}`, which also allows the artist a result was shared
with to view it (`require_viewable`) — mirrors
`app/api/routes/previews.py` exactly, since this is the same "private,
user-owned generated content, optionally shared with one booking's artist"
shape hand/foot previews already established.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.models.ai import AiDesignRequest, AiGeneration
from app.db.models.booking import Booking
from app.db.session import get_db_session
from app.schemas.ai_design import (
    AiDesignRequestListOut,
    AiDesignRequestOut,
    DesignGenerationRequest,
    SendDesignRequestToArtistRequest,
    ShareDesignRequestOut,
)
from app.schemas.design import PageInfo
from app.services.ai.design_generation import (
    AI_GENERATED_LABEL,
    create_design_request,
    delete_design_request,
    get_design_request_or_404,
    get_signed_result_url,
    require_owner,
    require_viewable,
    retry_design_request,
    save_design_request,
    send_design_request_to_artist,
    share_design_request,
    unsave_design_request,
)

router = APIRouter(prefix="/ai/designs", tags=["ai-designs"])

_HISTORY_SORT = "ai_design_request_history"


def _rate_limit() -> str:
    return get_settings().ai_design_rate_limit


def _get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError("Booking not found.", status_code=404)
    return booking


def _design_request_out(request: AiDesignRequest, generation: AiGeneration) -> AiDesignRequestOut:
    return AiDesignRequestOut(
        id=request.id,
        style=request.style,
        occasion=request.occasion,
        body_placement=request.body_placement,
        difficulty_level=request.difficulty_level,
        density=request.density,
        is_symmetric=request.is_symmetric,
        pattern_elements=request.pattern_elements,
        theme=request.theme,
        personalization_text=request.personalization_text,
        additional_instructions=request.additional_instructions,
        allow_provider_training=request.allow_provider_training,
        prompt=request.prompt,
        status=generation.status,
        provider=generation.provider,
        model_name=generation.model_name,
        cost_usd=float(generation.cost_usd) if generation.cost_usd is not None else None,
        requires_human_review=generation.requires_human_review,
        review_status=generation.review_status,
        error_message=generation.error_message,
        result_image_url=get_signed_result_url(request),
        is_ai_generated=request.is_ai_generated,
        ai_generated_label=AI_GENERATED_LABEL,
        retry_count=request.retry_count,
        max_retries=request.max_retries,
        is_saved=request.is_saved,
        saved_at=request.saved_at,
        shared_with_booking_id=request.shared_with_booking_id,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _get_generation_or_404(db: Session, request: AiDesignRequest) -> AiGeneration:
    generation = db.get(AiGeneration, request.generation_id)
    if generation is None:
        raise AppError("AI design request not found.", status_code=404)
    return generation


@router.post("", response_model=AiDesignRequestOut, status_code=202)
@limiter.limit(_rate_limit())
def create_ai_design(
    request: Request,
    payload: DesignGenerationRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestOut:
    design_request = create_design_request(
        db,
        user=current.user,
        style=payload.style,
        occasion=payload.occasion.value,
        body_placement=payload.body_placement.value,
        difficulty_level=payload.difficulty_level.value,
        density=payload.density.value,
        is_symmetric=payload.is_symmetric,
        pattern_elements=payload.pattern_elements,
        theme=payload.theme,
        personalization_text=payload.personalization_text,
        additional_instructions=payload.additional_instructions,
        allow_provider_training=payload.allow_provider_training,
    )
    db.commit()
    db.refresh(design_request)
    generation = _get_generation_or_404(db, design_request)
    return _design_request_out(design_request, generation)


@router.get("", response_model=AiDesignRequestListOut)
def list_ai_designs(
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestListOut:
    limit = max(1, min(limit, 100))
    stmt = select(AiDesignRequest).where(
        AiDesignRequest.user_id == current.user.id, AiDesignRequest.deleted_at.is_(None)
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_HISTORY_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(AiDesignRequest.created_at, AiDesignRequest.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(AiDesignRequest.created_at.desc(), AiDesignRequest.id.desc()).limit(
        limit + 1
    )
    requests = list(db.execute(stmt).scalars().all())
    has_more = len(requests) > limit
    page = requests[:limit]

    generations_by_id = {
        g.id: g
        for g in db.execute(
            select(AiGeneration).where(AiGeneration.id.in_([r.generation_id for r in page]))
        )
        .scalars()
        .all()
    }

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_HISTORY_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    return AiDesignRequestListOut(
        items=[
            _design_request_out(r, generations_by_id[r.generation_id])
            for r in page
            if r.generation_id in generations_by_id
        ],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{design_request_id}", response_model=AiDesignRequestOut)
def get_ai_design(
    design_request_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestOut:
    design_request = get_design_request_or_404(db, design_request_id)
    require_viewable(db, design_request, viewer=current.user)
    generation = _get_generation_or_404(db, design_request)
    return _design_request_out(design_request, generation)


@router.post("/{design_request_id}/retry", response_model=AiDesignRequestOut)
def retry_ai_design(
    design_request_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestOut:
    design_request = get_design_request_or_404(db, design_request_id)
    require_owner(design_request, user_id=current.user.id)
    retry_design_request(db, design_request, user=current.user)
    db.commit()
    db.refresh(design_request)
    generation = _get_generation_or_404(db, design_request)
    return _design_request_out(design_request, generation)


@router.post("/{design_request_id}/save", response_model=AiDesignRequestOut)
def save_ai_design(
    design_request_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestOut:
    design_request = get_design_request_or_404(db, design_request_id)
    require_owner(design_request, user_id=current.user.id)
    save_design_request(db, design_request)
    db.commit()
    db.refresh(design_request)
    generation = _get_generation_or_404(db, design_request)
    return _design_request_out(design_request, generation)


@router.delete("/{design_request_id}/save", response_model=AiDesignRequestOut)
def unsave_ai_design(
    design_request_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestOut:
    design_request = get_design_request_or_404(db, design_request_id)
    require_owner(design_request, user_id=current.user.id)
    unsave_design_request(db, design_request)
    db.commit()
    db.refresh(design_request)
    generation = _get_generation_or_404(db, design_request)
    return _design_request_out(design_request, generation)


@router.get("/{design_request_id}/share", response_model=ShareDesignRequestOut)
def share_ai_design(
    design_request_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ShareDesignRequestOut:
    design_request = get_design_request_or_404(db, design_request_id)
    require_owner(design_request, user_id=current.user.id)
    url, expires_in_seconds = share_design_request(design_request)
    return ShareDesignRequestOut(url=url, expires_in_seconds=expires_in_seconds)


@router.post("/{design_request_id}/send-to-artist", response_model=AiDesignRequestOut)
def send_ai_design_to_artist(
    design_request_id: uuid.UUID,
    payload: SendDesignRequestToArtistRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AiDesignRequestOut:
    design_request = get_design_request_or_404(db, design_request_id)
    require_owner(design_request, user_id=current.user.id)
    booking = _get_booking_or_404(db, payload.booking_id)

    send_design_request_to_artist(db, design_request, sender=current.user, booking=booking)
    db.commit()
    db.refresh(design_request)
    generation = _get_generation_or_404(db, design_request)
    return _design_request_out(design_request, generation)


@router.delete("/{design_request_id}", status_code=204)
def delete_ai_design(
    design_request_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    design_request = get_design_request_or_404(db, design_request_id)
    require_owner(design_request, user_id=current.user.id)
    delete_design_request(db, design_request)
    db.commit()
