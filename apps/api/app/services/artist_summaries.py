"""Shared `ArtistProfileOut`/`ArtistDocumentOut` construction — used by both
`app/api/routes/artist_onboarding.py` (the artist's own view) and
`app/api/routes/admin_artist_verification.py` (staff review), so the two
never drift out of sync. Mirrors app/services/design_summaries.py's role for
`DesignSummaryOut`.
"""

from sqlalchemy.orm import Session

from app.db.enums import ARTIST_PROFILE_EDITABLE_STATUSES
from app.db.models.artist import ArtistDocument, ArtistProfile
from app.integrations import supabase_storage
from app.schemas.artist import ArtistDocumentOut, ArtistProfileOut
from app.services.artist_verification import missing_submission_requirements

VERIFICATION_DOCUMENTS_BUCKET = "verification-documents"
DOCUMENT_VIEW_URL_TTL_SECONDS = 300


def artist_document_out(document: ArtistDocument) -> ArtistDocumentOut:
    view_url = supabase_storage.create_signed_url(
        bucket=VERIFICATION_DOCUMENTS_BUCKET,
        path=document.storage_path,
        expires_in_seconds=DOCUMENT_VIEW_URL_TTL_SECONDS,
    )
    return ArtistDocumentOut(
        id=document.id,
        document_type=document.document_type,
        original_filename=document.original_filename,
        content_type=document.content_type,
        file_size_bytes=document.file_size_bytes,
        status=document.status,
        rejection_reason=document.rejection_reason,
        reviewed_at=document.reviewed_at,
        view_url=view_url,
        created_at=document.created_at,
    )


def artist_profile_out(
    db: Session, profile: ArtistProfile, *, viewed_by_owner: bool
) -> ArtistProfileOut:
    """`is_editable` only reflects the *owner's* ability to edit — always
    False from a staff reviewer's point of view, since it isn't a
    meaningful concept for them."""
    return ArtistProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        professional_name=profile.professional_name,
        business_name=profile.business_name,
        headline=profile.headline,
        bio=profile.bio,
        years_experience=profile.years_experience,
        country=profile.country,
        city=profile.city,
        service_areas=profile.service_areas or [],
        languages=profile.languages or [],
        contact_email=profile.contact_email,
        contact_phone=profile.contact_phone,
        social_links=profile.social_links or {},
        profile_image_url=profile.profile_image_url,
        cover_image_url=profile.cover_image_url,
        verification_status=profile.verification_status,
        submitted_at=profile.submitted_at,
        reviewed_at=profile.reviewed_at,
        rejection_reason=profile.rejection_reason,
        more_info_request=profile.more_info_request,
        is_editable=viewed_by_owner
        and profile.verification_status in ARTIST_PROFILE_EDITABLE_STATUSES,
        missing_requirements=missing_submission_requirements(db, profile),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
