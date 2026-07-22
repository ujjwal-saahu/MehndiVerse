"""Hand/foot design preview projects — see docs/hand-foot-preview.md.

Compositing (drawing the transparent design overlay onto the hand/foot
photo at whatever position/scale/rotation/flip/opacity the user chose) is
entirely a client-side operation — this module never rasterizes an image
itself. It only ever handles two kinds of image bytes: the source photo
(uploaded once the user chooses to *save* a project — never before, per
docs/hand-foot-preview.md#do-not-upload-private-photos-unless-required) and
the already-composited export a client sends when the user chooses to
*export*.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, AuthorizationError
from app.core.images import ProcessedImage, process_preview_photo_upload
from app.db.enums import AnalyticsEventType, DesignStatus, PreviewProjectStatus
from app.db.models.ai import PreviewProject
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.design import Design
from app.db.models.user import User
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError
from app.services.analytics.events import record_event
from app.services.entitlements import get_effective_features
from app.services.messaging import get_or_create_booking_conversation, send_message

PREVIEW_BUCKET = "preview-projects"
# Long enough for one active viewing/editing session, short enough that a
# leaked link goes stale quickly — see docs/hand-foot-preview.md#secure-
# storage.
VIEW_URL_TTL_SECONDS = 600
# "Share" is an explicit, deliberate action (native share sheet / copy
# link) — a slightly longer window than a normal view, still never durable.
SHARE_URL_TTL_SECONDS = 3600


def _storage_prefix(*, user_id: uuid.UUID, preview_id: uuid.UUID) -> str:
    return f"{user_id}/{preview_id}"


def _require_premium_access_if_needed(db: Session, user: User, design: Design) -> None:
    if not design.is_premium:
        return
    features = get_effective_features(db, user)
    if not features.get("premium_design_access", False):
        raise AppError("This design is only available to premium subscribers.", status_code=403)


def _get_published_design_or_404(db: Session, design_id: uuid.UUID) -> Design:
    design = db.get(Design, design_id)
    if (
        design is None
        or design.deleted_at is not None
        or design.status != DesignStatus.PUBLISHED.value
    ):
        raise AppError("Design not found.", status_code=404)
    return design


def get_preview_or_404(db: Session, preview_id: uuid.UUID) -> PreviewProject:
    preview = db.get(PreviewProject, preview_id)
    if preview is None or preview.deleted_at is not None:
        raise AppError("Preview project not found.", status_code=404)
    return preview


def require_viewable(db: Session, preview: PreviewProject, *, viewer: User) -> None:
    """The owner may always view their own preview; the artist on the
    booking it was shared with (§send-to-artist) may view it too. Nobody
    else — this is a private photo, not published content."""
    if preview.user_id == viewer.id:
        return
    if preview.shared_with_booking_id is not None:
        booking = db.get(Booking, preview.shared_with_booking_id)
        if booking is not None:
            artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
            if artist_profile is not None and artist_profile.user_id == viewer.id:
                return
    raise AuthorizationError("You do not have access to this preview.")


def require_owner(preview: PreviewProject, *, user_id: uuid.UUID) -> None:
    if preview.user_id != user_id:
        raise AuthorizationError("You do not have access to this preview.")


def _upload_or_422(*, path: str, processed: ProcessedImage) -> None:
    try:
        supabase_storage.upload_private_object(
            bucket=PREVIEW_BUCKET,
            path=path,
            data=processed.data,
            content_type=processed.content_type,
        )
    except SupabaseStorageError as exc:
        raise AppError("Failed to upload image. Please try again.", status_code=502) from exc


def create_preview(
    db: Session,
    *,
    user: User,
    design_id: uuid.UUID | None,
    overlay_transform: dict[str, object] | None,
    raw_photo: bytes,
) -> PreviewProject:
    design: Design | None = None
    if design_id is not None:
        design = _get_published_design_or_404(db, design_id)
        _require_premium_access_if_needed(db, user, design)

    processed = process_preview_photo_upload(raw_photo)

    preview_id = uuid.uuid4()
    path = f"{_storage_prefix(user_id=user.id, preview_id=preview_id)}/source.{processed.extension}"
    _upload_or_422(path=path, processed=processed)

    preview = PreviewProject(
        id=preview_id,
        user_id=user.id,
        design_id=design.id if design is not None else None,
        source_storage_path=path,
        source_width=processed.width,
        source_height=processed.height,
        overlay_transform=overlay_transform,
        status=PreviewProjectStatus.COMPLETED.value,
    )
    db.add(preview)
    db.flush()
    record_event(
        db,
        event_type=AnalyticsEventType.PREVIEW_CREATED.value,
        user_id=user.id,
        entity_type="preview",
        entity_id=preview.id,
    )
    return preview


def update_preview(
    db: Session,
    preview: PreviewProject,
    *,
    user: User,
    design_id: uuid.UUID | None,
    overlay_transform: dict[str, object] | None,
    raw_photo: bytes | None,
) -> PreviewProject:
    """Re-editing an existing project: switch the design, adjust the
    overlay transform ("layer reset" is just the client sending back the
    default transform here), and/or replace the source photo — all
    optional and independently updatable."""
    if design_id is not None:
        design = _get_published_design_or_404(db, design_id)
        _require_premium_access_if_needed(db, user, design)
        preview.design_id = design.id

    if overlay_transform is not None:
        preview.overlay_transform = overlay_transform

    if raw_photo is not None:
        processed = process_preview_photo_upload(raw_photo)
        old_path = preview.source_storage_path
        new_path = (
            f"{_storage_prefix(user_id=user.id, preview_id=preview.id)}/source."
            f"{processed.extension}"
        )
        _upload_or_422(path=new_path, processed=processed)
        if old_path != new_path:
            _best_effort_delete(old_path)
        preview.source_storage_path = new_path
        preview.source_width = processed.width
        preview.source_height = processed.height
        # A new source photo invalidates any previously exported composite.
        if preview.result_storage_path is not None:
            _best_effort_delete(preview.result_storage_path)
            preview.result_storage_path = None

    db.add(preview)
    db.flush()
    return preview


def export_preview(
    db: Session, preview: PreviewProject, *, raw_composited_image: bytes
) -> PreviewProject:
    """`raw_composited_image` is the already-flattened photo+overlay
    composite a client renders locally (canvas/RepaintBoundary) — this
    function just validates and stores it, exactly like a source photo."""
    processed = process_preview_photo_upload(raw_composited_image)
    old_path = preview.result_storage_path
    new_path = (
        f"{_storage_prefix(user_id=preview.user_id, preview_id=preview.id)}/result."
        f"{processed.extension}"
    )
    _upload_or_422(path=new_path, processed=processed)
    if old_path is not None and old_path != new_path:
        _best_effort_delete(old_path)
    preview.result_storage_path = new_path
    db.add(preview)
    db.flush()
    return preview


def get_signed_source_url(
    preview: PreviewProject, *, expires_in_seconds: int = VIEW_URL_TTL_SECONDS
) -> str:
    return supabase_storage.create_signed_url(
        bucket=PREVIEW_BUCKET,
        path=preview.source_storage_path,
        expires_in_seconds=expires_in_seconds,
    )


def get_signed_result_url(
    preview: PreviewProject, *, expires_in_seconds: int = VIEW_URL_TTL_SECONDS
) -> str | None:
    if preview.result_storage_path is None:
        return None
    return supabase_storage.create_signed_url(
        bucket=PREVIEW_BUCKET,
        path=preview.result_storage_path,
        expires_in_seconds=expires_in_seconds,
    )


def share_preview(preview: PreviewProject) -> tuple[str, int]:
    """Shares the export if one exists, otherwise the plain source photo —
    either way, a fresh short-lived signed URL, never a durable link."""
    path = preview.result_storage_path or preview.source_storage_path
    url = supabase_storage.create_signed_url(
        bucket=PREVIEW_BUCKET, path=path, expires_in_seconds=SHARE_URL_TTL_SECONDS
    )
    return url, SHARE_URL_TTL_SECONDS


def send_to_artist(db: Session, preview: PreviewProject, *, sender: User, booking: Booking) -> None:
    if booking.customer_id != sender.id:
        raise AuthorizationError("You do not have access to this booking.")

    conversation = get_or_create_booking_conversation(db, booking)
    preview.shared_with_booking_id = booking.id
    db.add(preview)

    send_message(
        db,
        conversation,
        sender_id=sender.id,
        body="Shared a mehndi design preview — open your previews to view it.",
        attachment_url=None,
    )
    db.flush()


def _best_effort_delete(path: str) -> None:
    try:
        supabase_storage.delete_object(bucket=PREVIEW_BUCKET, path=path)
    except SupabaseStorageError:
        # The database row is the source of truth for "this preview is
        # gone" — a storage cleanup failure shouldn't block that.
        pass


def delete_preview(db: Session, preview: PreviewProject) -> None:
    preview.deleted_at = datetime.now(UTC)
    db.add(preview)
    _best_effort_delete(preview.source_storage_path)
    if preview.result_storage_path is not None:
        _best_effort_delete(preview.result_storage_path)
    db.flush()
