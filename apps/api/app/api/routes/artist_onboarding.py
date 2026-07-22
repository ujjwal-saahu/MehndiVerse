"""Artist onboarding — see docs/artist-verification.md.

Self-service: any non-staff authenticated user can start an application
(`GET /artist/profile` lazily creates a draft and flips their stored role to
`artist` on first call, the same "lazy provisioning" pattern
`get_current_user` already uses for the `User` row itself). Becoming
`verified_artist` (the effective role that unlocks full artist features)
still requires staff approval — see app/api/routes/admin_artist_verification.py.
"""

import uuid

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.documents import InvalidDocumentError, process_document_upload
from app.core.exceptions import AppError
from app.core.images import MAX_DESIGN_IMAGE_BYTES, InvalidImageError, process_image_upload
from app.db.enums import ARTIST_PROFILE_EDITABLE_STATUSES, DesignStatus, DocumentType, UserRole
from app.db.models.artist import ArtistDocument, ArtistProfile
from app.db.models.design import Design
from app.db.session import get_db_session
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError
from app.schemas.artist import (
    ArtistDocumentOut,
    ArtistImageUploadResponse,
    ArtistProfileOut,
    ArtistProfileUpdateRequest,
)
from app.schemas.artist_directory import PortfolioAnalyticsOut
from app.services.artist_summaries import (
    VERIFICATION_DOCUMENTS_BUCKET,
    artist_document_out,
    artist_profile_out,
)
from app.services.artist_verification import get_or_create_draft_profile, submit_for_review
from app.services.audit import record_audit_log
from app.services.design_summaries import summaries_for_designs

router = APIRouter(prefix="/artist", tags=["artist-onboarding"])

_STAFF_ROLES = {
    UserRole.MODERATOR.value,
    UserRole.ADMINISTRATOR.value,
    UserRole.SUPER_ADMINISTRATOR.value,
}
_VALID_DOCUMENT_TYPES = {member.value for member in DocumentType}


def _get_own_profile_or_404(db: Session, current: AuthenticatedUser) -> ArtistProfile:
    profile = db.execute(
        select(ArtistProfile).where(
            ArtistProfile.user_id == current.user.id, ArtistProfile.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("You haven't started an artist application yet.", status_code=404)
    return profile


def _require_editable(profile: ArtistProfile) -> None:
    if profile.verification_status not in ARTIST_PROFILE_EDITABLE_STATUSES:
        raise AppError(
            f"Your application can't be edited while it's '{profile.verification_status}'.",
            status_code=422,
        )


@router.get("/profile", response_model=ArtistProfileOut)
def get_my_artist_profile(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    if current.user.role in _STAFF_ROLES:
        raise AppError("Staff accounts cannot create an artist profile.", status_code=403)

    profile = get_or_create_draft_profile(db, user_id=current.user.id)
    if current.user.role == UserRole.CUSTOMER.value:
        current.user.role = UserRole.ARTIST.value
        db.add(current.user)
    db.commit()
    db.refresh(profile)
    return artist_profile_out(db, profile, viewed_by_owner=True)


@router.patch("/profile", response_model=ArtistProfileOut)
def update_my_artist_profile(
    payload: ArtistProfileUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_own_profile_or_404(db, current)
    _require_editable(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return artist_profile_out(db, profile, viewed_by_owner=True)


@router.post("/profile/submit", response_model=ArtistProfileOut)
def submit_my_artist_profile(
    request: Request,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistProfileOut:
    profile = _get_own_profile_or_404(db, current)
    before_status = profile.verification_status

    submit_for_review(db, profile)

    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="artist_verification.submit",
        entity_type="artist_profiles",
        entity_id=profile.id,
        before_state={"verification_status": before_status},
        after_state={"verification_status": profile.verification_status},
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return artist_profile_out(db, profile, viewed_by_owner=True)


def _upload_profile_image(
    file: UploadFile, *, current: AuthenticatedUser, db: Session, field: str, path_suffix: str
) -> ArtistImageUploadResponse:
    """Shared by the profile-image and cover-image endpoints below. These are
    public marketing images (shown on the artist's storefront), not
    verification evidence — they reuse the `portfolio` bucket's existing
    public-read/owner-write policy (see infrastructure/supabase/
    storage_policies.sql) rather than the private verification-documents
    bucket."""
    profile = _get_own_profile_or_404(db, current)

    raw = file.file.read()
    try:
        processed = process_image_upload(raw, max_bytes=MAX_DESIGN_IMAGE_BYTES)
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc

    path = f"{current.user.id}/{path_suffix}.{processed.extension}"
    try:
        image_url = supabase_storage.upload_object(
            bucket="portfolio", path=path, data=processed.data, content_type=processed.content_type
        )
    except SupabaseStorageError as exc:
        raise AppError("Failed to upload image. Please try again.", status_code=502) from exc

    setattr(profile, field, image_url)
    db.add(profile)
    db.commit()
    return ArtistImageUploadResponse(image_url=image_url)


@router.post("/profile/image", response_model=ArtistImageUploadResponse)
def upload_my_artist_profile_image(
    file: UploadFile,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistImageUploadResponse:
    return _upload_profile_image(
        file, current=current, db=db, field="profile_image_url", path_suffix="profile-image"
    )


@router.post("/profile/cover-image", response_model=ArtistImageUploadResponse)
def upload_my_artist_cover_image(
    file: UploadFile,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistImageUploadResponse:
    return _upload_profile_image(
        file, current=current, db=db, field="cover_image_url", path_suffix="cover-image"
    )


@router.get("/documents", response_model=list[ArtistDocumentOut])
def list_my_artist_documents(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ArtistDocumentOut]:
    profile = _get_own_profile_or_404(db, current)
    documents = db.execute(
        select(ArtistDocument)
        .where(ArtistDocument.artist_profile_id == profile.id)
        .order_by(ArtistDocument.created_at.desc())
    ).scalars()
    return [artist_document_out(document) for document in documents]


@router.post("/documents", response_model=ArtistDocumentOut, status_code=201)
async def upload_my_artist_document(
    file: UploadFile,
    document_type: str = Form(...),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ArtistDocumentOut:
    profile = _get_own_profile_or_404(db, current)
    _require_editable(profile)

    if document_type not in _VALID_DOCUMENT_TYPES:
        raise AppError(
            f"document_type must be one of: {', '.join(sorted(_VALID_DOCUMENT_TYPES))}",
            status_code=422,
        )

    raw = await file.read()
    try:
        processed = process_document_upload(raw, content_type=file.content_type or "")
    except InvalidDocumentError as exc:
        raise AppError(str(exc), status_code=422) from exc

    document_id = uuid.uuid4()
    storage_path = f"{current.user.id}/{document_id}.{processed.extension}"
    try:
        supabase_storage.upload_private_object(
            bucket=VERIFICATION_DOCUMENTS_BUCKET,
            path=storage_path,
            data=processed.data,
            content_type=processed.content_type,
        )
    except SupabaseStorageError as exc:
        raise AppError("Failed to upload document. Please try again.", status_code=502) from exc

    document = ArtistDocument(
        id=document_id,
        artist_profile_id=profile.id,
        document_type=document_type,
        storage_path=storage_path,
        original_filename=file.filename,
        content_type=processed.content_type,
        file_size_bytes=len(processed.data),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return artist_document_out(document)


_ANALYTICS_TOP_DESIGNS_LIMIT = 5


@router.get("/portfolio/analytics", response_model=PortfolioAnalyticsOut)
def get_my_portfolio_analytics(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PortfolioAnalyticsOut:
    """Foundation-level aggregate — total counts plus a top-5-by-views list,
    no time-series/date-bucketing. See
    docs/artist-directory.md#portfolio-analytics-is-a-foundation."""
    profile = _get_own_profile_or_404(db, current)

    totals = db.execute(
        select(
            func.count(Design.id),
            func.count(Design.id).filter(Design.status == DesignStatus.PUBLISHED.value),
            func.coalesce(func.sum(Design.view_count), 0),
            func.coalesce(func.sum(Design.like_count), 0),
            func.coalesce(func.sum(Design.save_count), 0),
        ).where(Design.artist_profile_id == profile.id, Design.deleted_at.is_(None))
    ).one()
    total_designs, published_designs, total_views, total_likes, total_saves = totals

    top_designs = (
        db.execute(
            select(Design)
            .where(Design.artist_profile_id == profile.id, Design.deleted_at.is_(None))
            .order_by(Design.view_count.desc(), Design.id.desc())
            .limit(_ANALYTICS_TOP_DESIGNS_LIMIT)
        )
        .scalars()
        .all()
    )

    return PortfolioAnalyticsOut(
        total_designs=total_designs,
        published_designs=published_designs,
        total_views=int(total_views),
        total_likes=int(total_likes),
        total_saves=int(total_saves),
        top_designs=summaries_for_designs(db, list(top_designs)),
    )
