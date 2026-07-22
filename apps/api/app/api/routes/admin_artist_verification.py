"""Staff-side artist verification review — see docs/artist-verification.md.

Viewing the queue/detail/documents/audit-log is available to `moderator`,
`admin`, and `super_admin` (mirrors designs.py's `_VIEW_STAFF_ROLES`); only
`admin`/`super_admin` may actually act on an application (`_EDIT_STAFF_ROLES`)
— the same split Phase 6/7 already established for design moderation.
Every action endpoint also blocks a staff member from reviewing their *own*
artist profile, regardless of role — see
docs/artist-verification.md#preventing-self-approval.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, AuthorizationError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import ArtistVerificationStatus
from app.db.models.artist import ArtistDocument, ArtistProfile
from app.db.models.system import AuditLog
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.artist import (
    ArtistDocumentOut,
    ArtistProfileOut,
    ArtistRejectRequest,
    ArtistRequestMoreInfoRequest,
    ArtistSuspendRequest,
    ArtistVerificationQueueItemOut,
    ArtistVerificationQueueOut,
    AuditLogEntryOut,
    AuditLogListOut,
    DocumentReviewRequest,
)
from app.schemas.design import PageInfo
from app.services.artist_summaries import artist_document_out, artist_profile_out
from app.services.artist_verification import apply_staff_transition, review_document
from app.services.audit import record_audit_log

router = APIRouter(prefix="/admin/artists", tags=["admin-artist-verification"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_QUEUE_SORT = "artist_verification_queue"
_AUDIT_SORT = "artist_verification_audit"


def _get_profile_or_404(db: Session, artist_profile_id: uuid.UUID) -> ArtistProfile:
    profile = db.get(ArtistProfile, artist_profile_id)
    if profile is None or profile.deleted_at is not None:
        raise AppError("Artist profile not found.", status_code=404)
    return profile


def _require_not_self(profile: ArtistProfile, current: AuthenticatedUser) -> None:
    if profile.user_id == current.user.id:
        raise AuthorizationError("You cannot review your own artist application.")


def _apply_transition_and_respond(
    db: Session,
    request: Request,
    current: AuthenticatedUser,
    profile: ArtistProfile,
    *,
    to_status: str,
    action: str,
    reason: str | None,
) -> ArtistProfileOut:
    _require_not_self(profile, current)
    before_status = profile.verification_status

    apply_staff_transition(
        db, profile, to_status=to_status, reviewer_id=current.user.id, reason=reason
    )

    after_state: dict[str, object] = {"verification_status": profile.verification_status}
    if reason is not None:
        after_state["reason"] = reason
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action=f"artist_verification.{action}",
        entity_type="artist_profiles",
        entity_id=profile.id,
        before_state={"verification_status": before_status},
        after_state=after_state,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return artist_profile_out(db, profile, viewed_by_owner=False)


@router.get("", response_model=ArtistVerificationQueueOut)
def list_verification_queue(
    status_filter: list[str] | None = Query(default=None),
    search: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistVerificationQueueOut:
    """Also backs the "Artist management" dashboard module (see
    docs/admin-dashboard.md#artist-management) — pass every status via
    `status_filter` to browse all artists rather than just the review
    queue, and `search` to filter by professional/business name."""
    limit = max(1, min(limit, 100))
    statuses = status_filter or [
        ArtistVerificationStatus.SUBMITTED.value,
        ArtistVerificationStatus.UNDER_REVIEW.value,
    ]
    unknown = set(statuses) - {member.value for member in ArtistVerificationStatus}
    if unknown:
        raise AppError(f"Unknown status filter(s): {', '.join(sorted(unknown))}", status_code=422)

    # Oldest submission first — a FIFO review queue. Rows with no
    # `submitted_at` (shouldn't normally be queried here, but defensively)
    # sort last.
    stmt = select(ArtistProfile).where(
        ArtistProfile.verification_status.in_(statuses), ArtistProfile.deleted_at.is_(None)
    )
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(ArtistProfile.professional_name).like(needle)
            | func.lower(ArtistProfile.business_name).like(needle)
        )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_QUEUE_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_submitted_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(ArtistProfile.submitted_at, ArtistProfile.id)
            > tuple_(literal(cursor_submitted_at), literal(decoded.id))
        )
    stmt = stmt.order_by(ArtistProfile.submitted_at.asc(), ArtistProfile.id.asc()).limit(limit + 1)

    profiles = list(db.execute(stmt).scalars().all())
    has_more = len(profiles) > limit
    page = profiles[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_QUEUE_SORT,
            sort_value=(last.submitted_at or last.created_at).isoformat(),
            id_=last.id,
        )

    counts: dict[uuid.UUID, int] = {}
    if page:
        count_rows = db.execute(
            select(ArtistDocument.artist_profile_id, func.count(ArtistDocument.id))
            .where(ArtistDocument.artist_profile_id.in_([p.id for p in page]))
            .group_by(ArtistDocument.artist_profile_id)
        ).all()
        counts = {profile_id: count for profile_id, count in count_rows}

    items = [
        ArtistVerificationQueueItemOut(
            id=profile.id,
            user_id=profile.user_id,
            professional_name=profile.professional_name,
            business_name=profile.business_name,
            verification_status=profile.verification_status,
            submitted_at=profile.submitted_at,
            document_count=counts.get(profile.id, 0),
        )
        for profile in page
    ]
    return ArtistVerificationQueueOut(
        items=items, page_info=PageInfo(next_cursor=next_cursor, has_more=has_more)
    )


@router.get("/{artist_profile_id}", response_model=ArtistProfileOut)
def get_artist_verification_detail(
    artist_profile_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    return artist_profile_out(db, profile, viewed_by_owner=False)


@router.get("/{artist_profile_id}/documents", response_model=list[ArtistDocumentOut])
def list_artist_verification_documents(
    artist_profile_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[ArtistDocumentOut]:
    profile = _get_profile_or_404(db, artist_profile_id)
    documents = db.execute(
        select(ArtistDocument)
        .where(ArtistDocument.artist_profile_id == profile.id)
        .order_by(ArtistDocument.created_at.desc())
    ).scalars()
    return [artist_document_out(document) for document in documents]


@router.get("/{artist_profile_id}/audit-log", response_model=AuditLogListOut)
def list_artist_verification_audit_log(
    artist_profile_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AuditLogListOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    limit = max(1, min(limit, 100))

    stmt = select(AuditLog).where(
        AuditLog.entity_type == "artist_profiles", AuditLog.entity_id == profile.id
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_AUDIT_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(AuditLog.created_at, AuditLog.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1)

    entries = list(db.execute(stmt).scalars().all())
    has_more = len(entries) > limit
    page = entries[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_AUDIT_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    actor_ids = [entry.actor_id for entry in page if entry.actor_id is not None]
    names_by_actor: dict[uuid.UUID, str] = {}
    if actor_ids:
        rows = db.execute(
            select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(actor_ids))
        ).all()
        names_by_actor = {user_id: name for user_id, name in rows}

    items = [
        AuditLogEntryOut(
            id=entry.id,
            actor_id=entry.actor_id,
            actor_display_name=names_by_actor.get(entry.actor_id) if entry.actor_id else None,
            action=entry.action,
            before_state=entry.before_state,
            after_state=entry.after_state,
            created_at=entry.created_at,
        )
        for entry in page
    ]
    return AuditLogListOut(
        items=items, page_info=PageInfo(next_cursor=next_cursor, has_more=has_more)
    )


@router.post("/{artist_profile_id}/start-review", response_model=ArtistProfileOut)
def start_artist_review(
    artist_profile_id: uuid.UUID,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    return _apply_transition_and_respond(
        db,
        request,
        current,
        profile,
        to_status=ArtistVerificationStatus.UNDER_REVIEW.value,
        action="start_review",
        reason=None,
    )


@router.post("/{artist_profile_id}/approve", response_model=ArtistProfileOut)
def approve_artist(
    artist_profile_id: uuid.UUID,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    return _apply_transition_and_respond(
        db,
        request,
        current,
        profile,
        to_status=ArtistVerificationStatus.APPROVED.value,
        action="approve",
        reason=None,
    )


@router.post("/{artist_profile_id}/reject", response_model=ArtistProfileOut)
def reject_artist(
    artist_profile_id: uuid.UUID,
    payload: ArtistRejectRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    return _apply_transition_and_respond(
        db,
        request,
        current,
        profile,
        to_status=ArtistVerificationStatus.REJECTED.value,
        action="reject",
        reason=payload.reason,
    )


@router.post("/{artist_profile_id}/request-more-information", response_model=ArtistProfileOut)
def request_more_information(
    artist_profile_id: uuid.UUID,
    payload: ArtistRequestMoreInfoRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    return _apply_transition_and_respond(
        db,
        request,
        current,
        profile,
        to_status=ArtistVerificationStatus.MORE_INFORMATION_REQUIRED.value,
        action="request_more_information",
        reason=payload.message,
    )


@router.post("/{artist_profile_id}/suspend", response_model=ArtistProfileOut)
def suspend_artist(
    artist_profile_id: uuid.UUID,
    payload: ArtistSuspendRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    return _apply_transition_and_respond(
        db,
        request,
        current,
        profile,
        to_status=ArtistVerificationStatus.SUSPENDED.value,
        action="suspend",
        reason=payload.reason,
    )


@router.post("/{artist_profile_id}/reactivate", response_model=ArtistProfileOut)
def reactivate_artist(
    artist_profile_id: uuid.UUID,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    """Undoes `suspend` — see docs/admin-dashboard.md#artist-management. Only
    valid from `suspended` (`is_valid_artist_staff_transition` enforces this
    the same way every other transition here is enforced)."""
    profile = _get_profile_or_404(db, artist_profile_id)
    return _apply_transition_and_respond(
        db,
        request,
        current,
        profile,
        to_status=ArtistVerificationStatus.APPROVED.value,
        action="reactivate",
        reason=None,
    )


@router.patch("/{artist_profile_id}/documents/{document_id}", response_model=ArtistDocumentOut)
def review_artist_document(
    artist_profile_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: DocumentReviewRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistDocumentOut:
    profile = _get_profile_or_404(db, artist_profile_id)
    _require_not_self(profile, current)

    document = db.get(ArtistDocument, document_id)
    if document is None or document.artist_profile_id != profile.id:
        raise AppError("Document not found.", status_code=404)

    before_status = document.status
    review_document(
        db,
        document,
        status=payload.status,
        reviewer_id=current.user.id,
        rejection_reason=payload.rejection_reason,
    )

    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="artist_document.review",
        entity_type="artist_documents",
        entity_id=document.id,
        before_state={"status": before_status},
        after_state={"status": document.status, "rejection_reason": document.rejection_reason},
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return artist_document_out(document)
