"""Artist onboarding and verification-lifecycle writes — see
docs/artist-verification.md.

Pure state-transition *validation* lives in app/db/enums.py
(`is_valid_artist_self_transition`/`is_valid_artist_staff_transition`); this
module wraps that with the actual row writes (status column, timestamps,
review fields) each transition needs, plus submission-readiness checks and
document review. Callers (the route layer) are responsible for
authorization — including the "an admin can never act on their own artist
profile" rule, which is a route-layer guard since it needs the *caller's*
identity, not just the target profile's.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import (
    ArtistVerificationStatus,
    DocumentStatus,
    DocumentType,
    is_valid_artist_self_transition,
    is_valid_artist_staff_transition,
)
from app.db.models.artist import ArtistDocument, ArtistProfile

# Fields an application must have filled in before it can be submitted for
# review. Documents are checked separately (at least one non-rejected
# id_proof) since they're a different table.
REQUIRED_SUBMISSION_FIELDS: tuple[str, ...] = (
    "professional_name",
    "bio",
    "years_experience",
    "country",
    "city",
)


def get_or_create_draft_profile(db: Session, *, user_id: uuid.UUID) -> ArtistProfile:
    profile = db.execute(
        select(ArtistProfile).where(
            ArtistProfile.user_id == user_id, ArtistProfile.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if profile is not None:
        return profile

    profile = ArtistProfile(
        user_id=user_id, verification_status=ArtistVerificationStatus.DRAFT.value
    )
    db.add(profile)
    db.flush()
    return profile


def missing_submission_requirements(db: Session, profile: ArtistProfile) -> list[str]:
    """Returns the empty list if `profile` is ready to submit."""
    missing = [field for field in REQUIRED_SUBMISSION_FIELDS if not getattr(profile, field)]

    has_id_proof = db.execute(
        select(ArtistDocument.id).where(
            ArtistDocument.artist_profile_id == profile.id,
            ArtistDocument.document_type == DocumentType.ID_PROOF.value,
            ArtistDocument.status != DocumentStatus.REJECTED.value,
        )
    ).first()
    if has_id_proof is None:
        missing.append("identity_document")

    return missing


def submit_for_review(db: Session, profile: ArtistProfile) -> None:
    to_status = ArtistVerificationStatus.SUBMITTED.value
    if not is_valid_artist_self_transition(profile.verification_status, to_status):
        raise AppError(
            f"Cannot submit an application with status '{profile.verification_status}'.",
            status_code=422,
        )
    missing = missing_submission_requirements(db, profile)
    if missing:
        raise AppError(
            f"Your application is missing required information: {', '.join(missing)}.",
            status_code=422,
        )

    profile.verification_status = to_status
    profile.submitted_at = datetime.now(UTC)
    profile.rejection_reason = None
    profile.more_info_request = None


def apply_staff_transition(
    db: Session,
    profile: ArtistProfile,
    *,
    to_status: str,
    reviewer_id: uuid.UUID,
    reason: str | None = None,
) -> None:
    """`reason` is required (enforced by the request schema, not here) for
    reject/suspend (the message shown to the artist) and
    more_information_required (what's still needed); ignored otherwise."""
    if not is_valid_artist_staff_transition(profile.verification_status, to_status):
        raise AppError(
            f"Cannot move an application from '{profile.verification_status}' to '{to_status}'.",
            status_code=422,
        )

    profile.verification_status = to_status
    profile.reviewed_at = datetime.now(UTC)
    profile.reviewed_by = reviewer_id

    if to_status in (
        ArtistVerificationStatus.REJECTED.value,
        ArtistVerificationStatus.SUSPENDED.value,
    ):
        profile.rejection_reason = reason
        profile.more_info_request = None
    elif to_status == ArtistVerificationStatus.MORE_INFORMATION_REQUIRED.value:
        profile.more_info_request = reason
        profile.rejection_reason = None
    else:
        # approved (from under_review or suspended) — clear any stale
        # reason/request text from a previous cycle.
        profile.rejection_reason = None
        profile.more_info_request = None


def review_document(
    db: Session,
    document: ArtistDocument,
    *,
    status: str,
    reviewer_id: uuid.UUID,
    rejection_reason: str | None = None,
) -> None:
    if status not in (DocumentStatus.APPROVED.value, DocumentStatus.REJECTED.value):
        raise AppError("A document can only be approved or rejected.", status_code=422)
    document.status = status
    document.reviewed_by = reviewer_id
    document.reviewed_at = datetime.now(UTC)
    document.rejection_reason = (
        rejection_reason if status == DocumentStatus.REJECTED.value else None
    )
