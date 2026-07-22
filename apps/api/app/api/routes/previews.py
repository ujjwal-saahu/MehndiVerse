"""Hand/foot design preview projects — see docs/hand-foot-preview.md.

The hand/foot photo is never uploaded just for local editing — a client
does all move/resize/rotate/flip/opacity editing itself, entirely offline,
and only calls `POST /previews` (or `PATCH .../export`) once the user
explicitly chooses to save/export/share/send. See
docs/hand-foot-preview.md#do-not-upload-private-photos-unless-required.
"""

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.images import InvalidImageError
from app.db.models.ai import PreviewProject
from app.db.models.booking import Booking
from app.db.models.design import Design
from app.db.session import get_db_session
from app.schemas.preview import (
    ExportPreviewOut,
    OverlayTransform,
    PreviewProjectOut,
    SendToArtistRequest,
    SharePreviewOut,
)
from app.services.design_summaries import summaries_for_designs
from app.services.previews import (
    create_preview,
    delete_preview,
    export_preview,
    get_preview_or_404,
    get_signed_result_url,
    get_signed_source_url,
    require_owner,
    require_viewable,
    send_to_artist,
    share_preview,
    update_preview,
)

router = APIRouter(prefix="/previews", tags=["previews"])


def _rate_limit() -> str:
    return get_settings().preview_rate_limit


def _parse_transform(raw: str | None) -> dict[str, object] | None:
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError("overlay_transform must be valid JSON.", status_code=422) from exc
    try:
        return OverlayTransform(**payload).model_dump()
    except ValidationError as exc:
        raise AppError(f"Invalid overlay_transform: {exc}", status_code=422) from exc


def _preview_out(db: Session, preview: PreviewProject) -> PreviewProjectOut:
    design_summary = None
    if preview.design_id is not None:
        design = db.get(Design, preview.design_id)
        if design is not None:
            summaries = summaries_for_designs(db, [design])
            design_summary = summaries[0] if summaries else None

    return PreviewProjectOut(
        id=preview.id,
        design=design_summary,
        source_image_url=get_signed_source_url(preview),
        result_image_url=get_signed_result_url(preview),
        overlay_transform=(
            OverlayTransform(**preview.overlay_transform) if preview.overlay_transform else None
        ),
        source_width=preview.source_width,
        source_height=preview.source_height,
        status=preview.status,
        error_message=preview.error_message,
        shared_with_booking_id=preview.shared_with_booking_id,
        created_at=preview.created_at,
        updated_at=preview.updated_at,
    )


def _get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError("Booking not found.", status_code=404)
    return booking


@router.post("", response_model=PreviewProjectOut, status_code=201)
@limiter.limit(_rate_limit())
async def create_preview_project(
    request: Request,
    file: UploadFile,
    design_id: str | None = Form(default=None),
    overlay_transform: str | None = Form(default=None),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PreviewProjectOut:
    raw = await file.read()
    try:
        preview = create_preview(
            db,
            user=current.user,
            design_id=uuid.UUID(design_id) if design_id else None,
            overlay_transform=_parse_transform(overlay_transform),
            raw_photo=raw,
        )
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc
    db.commit()
    db.refresh(preview)
    return _preview_out(db, preview)


@router.get("/mine", response_model=list[PreviewProjectOut])
def list_my_previews(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[PreviewProjectOut]:
    previews = (
        db.execute(
            select(PreviewProject)
            .where(PreviewProject.user_id == current.user.id, PreviewProject.deleted_at.is_(None))
            .order_by(PreviewProject.updated_at.desc())
        )
        .scalars()
        .all()
    )
    return [_preview_out(db, p) for p in previews]


@router.get("/{preview_id}", response_model=PreviewProjectOut)
def get_preview_project(
    preview_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PreviewProjectOut:
    preview = get_preview_or_404(db, preview_id)
    require_viewable(db, preview, viewer=current.user)
    return _preview_out(db, preview)


@router.patch("/{preview_id}", response_model=PreviewProjectOut)
@limiter.limit(_rate_limit())
async def update_preview_project(
    request: Request,
    preview_id: uuid.UUID,
    file: UploadFile | None = File(default=None),
    design_id: str | None = Form(default=None),
    overlay_transform: str | None = Form(default=None),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PreviewProjectOut:
    preview = get_preview_or_404(db, preview_id)
    require_owner(preview, user_id=current.user.id)

    raw_photo = await file.read() if file is not None else None
    try:
        preview = update_preview(
            db,
            preview,
            user=current.user,
            design_id=uuid.UUID(design_id) if design_id else None,
            overlay_transform=_parse_transform(overlay_transform),
            raw_photo=raw_photo,
        )
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc
    db.commit()
    db.refresh(preview)
    return _preview_out(db, preview)


@router.post("/{preview_id}/export", response_model=ExportPreviewOut)
@limiter.limit(_rate_limit())
async def export_preview_project(
    request: Request,
    preview_id: uuid.UUID,
    file: UploadFile,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ExportPreviewOut:
    preview = get_preview_or_404(db, preview_id)
    require_owner(preview, user_id=current.user.id)

    raw = await file.read()
    try:
        preview = export_preview(db, preview, raw_composited_image=raw)
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc
    db.commit()
    db.refresh(preview)
    result_url = get_signed_result_url(preview)
    assert result_url is not None
    return ExportPreviewOut(result_image_url=result_url)


@router.get("/{preview_id}/share", response_model=SharePreviewOut)
def share_preview_project(
    preview_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SharePreviewOut:
    preview = get_preview_or_404(db, preview_id)
    require_owner(preview, user_id=current.user.id)
    url, expires_in_seconds = share_preview(preview)
    return SharePreviewOut(url=url, expires_in_seconds=expires_in_seconds)


@router.post("/{preview_id}/send-to-artist", response_model=PreviewProjectOut)
def send_preview_to_artist(
    preview_id: uuid.UUID,
    payload: SendToArtistRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PreviewProjectOut:
    preview = get_preview_or_404(db, preview_id)
    require_owner(preview, user_id=current.user.id)
    booking = _get_booking_or_404(db, payload.booking_id)

    send_to_artist(db, preview, sender=current.user, booking=booking)
    db.commit()
    db.refresh(preview)
    return _preview_out(db, preview)


@router.delete("/{preview_id}", status_code=204)
def delete_preview_project(
    preview_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    preview = get_preview_or_404(db, preview_id)
    require_owner(preview, user_id=current.user.id)
    delete_preview(db, preview)
    db.commit()
