import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Response, UploadFile
from sqlalchemy import delete, func, literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, require_roles
from app.core.caching import set_public_cache
from app.core.exceptions import AppError, AuthorizationError
from app.core.images import (
    ALLOWED_CONTENT_TYPES,
    MAX_DESIGN_IMAGE_BYTES,
    InvalidImageError,
    process_image_upload,
)
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import (
    DESIGN_ARCHIVABLE_STATUSES,
    DesignImageStatus,
    DesignStatus,
    UsageType,
    is_valid_owner_design_transition,
)
from app.db.models.artist import ArtistProfile
from app.db.models.design import Category, Design, DesignCategory, DesignImage, DesignTag, Tag
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.design import (
    CategoryOut,
    DesignCreateRequest,
    DesignDownloadOut,
    DesignImageAuthorizeResponse,
    DesignImageOut,
    DesignListOut,
    DesignOut,
    DesignSummaryOut,
    DesignUpdateRequest,
    HomeFeedOut,
    PageInfo,
)
from app.services.ai.embeddings import enqueue_embedding_generation
from app.services.ai.flags import is_feature_enabled
from app.services.ai.moderation import enqueue_moderation_check
from app.services.ai.tagging import enqueue_tag_suggestion
from app.services.design_image_processing import queue_image_processing, storage_prefix
from app.services.design_summaries import (
    batch_artist_summaries,
    batch_primary_images,
    design_summary_out,
    summaries_for_designs,
)
from app.services.engagement import is_liked_by, is_saved_by
from app.services.entitlements import (
    check_and_increment_usage,
    get_effective_features,
    require_portfolio_capacity,
)
from app.services.view_tracking import record_design_view

router = APIRouter(prefix="/designs", tags=["designs"])

# Who may create/edit content vs. who may only view it for moderation
# purposes — see docs/design-catalog.md#ownership-and-permissions.
_CREATE_ROLES = ("artist", "verified_artist", "admin", "super_admin")
_EDIT_STAFF_ROLES = {"admin", "super_admin"}
_VIEW_STAFF_ROLES = {"moderator", "admin", "super_admin"}
# Only a verified (approved) artist or staff may mark a design premium — an
# artist whose application hasn't been approved yet shouldn't be able to
# gate content behind a trust signal nobody has vetted. See
# docs/artist-directory.md#premium-status-permission.
_PREMIUM_ROLES = {"verified_artist", "admin", "super_admin"}

_SORT_MODES = {"latest", "trending"}
_HOME_FEED_SECTION_LIMIT = 10
_RELATED_DESIGNS_LIMIT = 10


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tag"


def _is_owner(db: Session, design: Design, current: AuthenticatedUser) -> bool:
    if design.artist_profile_id is None:
        return False
    artist_profile = db.get(ArtistProfile, design.artist_profile_id)
    return artist_profile is not None and artist_profile.user_id == current.user.id


def _can_view_unpublished(db: Session, design: Design, current: AuthenticatedUser) -> bool:
    return current.effective_role in _VIEW_STAFF_ROLES or _is_owner(db, design, current)


def _can_edit(db: Session, design: Design, current: AuthenticatedUser) -> bool:
    return current.effective_role in _EDIT_STAFF_ROLES or _is_owner(db, design, current)


def _require_edit_permission(db: Session, design: Design, current: AuthenticatedUser) -> None:
    if not _can_edit(db, design, current):
        raise AuthorizationError("You do not own this design.")


def _queue_ai_jobs_for_new_image(db: Session, design: Design) -> None:
    """Fired once a design's image finishes processing (Step 8 of
    docs/design-catalog.md#image-upload-pipeline) — the earliest point a
    primary, ready image reliably exists for
    `app/services/ai/imaging.py::get_primary_ready_image_url` to find. Each
    capability is independently feature-flag-gated (see
    docs/ai-foundation.md#feature-flags); enqueuing is a fast INSERT so this
    never meaningfully slows the upload response (see docs/ai-foundation.md
    #ai-calls-must-not-block-api-workers)."""
    if is_feature_enabled(db, "tag_suggestions"):
        enqueue_tag_suggestion(db, design=design, triggered_by=None)
    if is_feature_enabled(db, "embeddings"):
        enqueue_embedding_generation(db, design=design, triggered_by=None)
    if is_feature_enabled(db, "moderation"):
        enqueue_moderation_check(db, design=design, triggered_by=None)


def _owning_user_id(db: Session, design: Design, current: AuthenticatedUser) -> uuid.UUID:
    if design.artist_profile_id is not None:
        artist_profile = db.get(ArtistProfile, design.artist_profile_id)
        if artist_profile is not None:
            return artist_profile.user_id
    return current.user.id


def _get_design_or_404(db: Session, design_id: uuid.UUID) -> Design:
    design = db.get(Design, design_id)
    if design is None or design.deleted_at is not None:
        raise AppError("Design not found.", status_code=404)
    return design


def _require_visible(db: Session, design: Design, current: AuthenticatedUser) -> bool:
    """Returns whether the caller may see non-published details/images;
    raises 404 if they can't see the design at all. See
    docs/design-gallery.md#public-visibility-filtering."""
    can_view_unpublished = _can_view_unpublished(db, design, current)
    if design.status != DesignStatus.PUBLISHED.value and not can_view_unpublished:
        raise AppError("Design not found.", status_code=404)
    return can_view_unpublished


def _sync_categories(db: Session, design_id: uuid.UUID, category_ids: list[uuid.UUID]) -> None:
    db.execute(delete(DesignCategory).where(DesignCategory.design_id == design_id))
    if not category_ids:
        return
    valid_ids = set(
        db.execute(select(Category.id).where(Category.id.in_(category_ids))).scalars().all()
    )
    unknown = set(category_ids) - valid_ids
    if unknown:
        raise AppError(
            f"Unknown category id(s): {', '.join(str(i) for i in unknown)}", status_code=422
        )
    db.add_all(DesignCategory(design_id=design_id, category_id=cid) for cid in category_ids)


def _sync_tags(db: Session, design_id: uuid.UUID, tag_names: list[str]) -> None:
    db.execute(delete(DesignTag).where(DesignTag.design_id == design_id))
    for name in tag_names:
        slug = _slugify(name)
        tag = db.execute(select(Tag).where(Tag.slug == slug)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name, slug=slug)
            db.add(tag)
            db.flush()
        db.add(DesignTag(design_id=design_id, tag_id=tag.id))


def _category_out(category: Category) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        category_type=category.category_type,
        description=category.description,
        parent_category_id=category.parent_category_id,
        sort_order=category.sort_order,
        is_active=category.is_active,
    )


def _design_image_out(image: DesignImage, *, premium_locked: bool) -> DesignImageOut:
    return DesignImageOut(
        id=image.id,
        design_id=image.design_id,
        status=image.status,
        # Locked: withhold the full-resolution/medium images, keep only the
        # small thumbnail as a preview — see
        # docs/subscriptions-and-entitlements.md#premium-design-access.
        image_url=None if premium_locked else image.image_url,
        thumbnail_small_url=image.thumbnail_small_url,
        thumbnail_medium_url=None if premium_locked else image.thumbnail_medium_url,
        width=image.width,
        height=image.height,
        sort_order=image.sort_order,
        is_primary=image.is_primary,
        processing_error=image.processing_error,
    )


def _design_out(
    db: Session,
    design: Design,
    *,
    include_non_ready_images: bool,
    current_user_id: uuid.UUID,
    viewer_has_premium_access: bool = True,
) -> DesignOut:
    categories = db.execute(
        select(Category)
        .join(DesignCategory, DesignCategory.category_id == Category.id)
        .where(DesignCategory.design_id == design.id)
        .order_by(Category.category_type, Category.sort_order)
    ).scalars()
    tags = db.execute(
        select(Tag.name)
        .join(DesignTag, DesignTag.tag_id == Tag.id)
        .where(DesignTag.design_id == design.id)
        .order_by(Tag.name)
    ).scalars()

    image_stmt = select(DesignImage).where(DesignImage.design_id == design.id)
    if not include_non_ready_images:
        image_stmt = image_stmt.where(DesignImage.status == DesignImageStatus.READY.value)
    image_stmt = image_stmt.order_by(DesignImage.sort_order)
    images = db.execute(image_stmt).scalars()

    artist = None
    if design.artist_profile_id is not None:
        artist = batch_artist_summaries(db, [design.artist_profile_id]).get(
            design.artist_profile_id
        )

    premium_locked = design.is_premium and not viewer_has_premium_access

    return DesignOut(
        id=design.id,
        artist_profile_id=design.artist_profile_id,
        artist=artist,
        title=design.title,
        description=design.description,
        difficulty_level=design.difficulty_level,
        body_placement=design.body_placement,
        status=design.status,
        is_featured=design.is_featured,
        is_premium=design.is_premium,
        premium_locked=premium_locked,
        view_count=design.view_count,
        like_count=design.like_count,
        save_count=design.save_count,
        is_liked=is_liked_by(db, user_id=current_user_id, design_id=design.id),
        is_saved=is_saved_by(db, user_id=current_user_id, design_id=design.id),
        categories=[_category_out(c) for c in categories],
        tags=list(tags),
        images=[_design_image_out(img, premium_locked=premium_locked) for img in images],
        created_at=design.created_at,
        updated_at=design.updated_at,
    )


def _order_and_cursor_columns(sort: str) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    if sort == "trending":
        return (Design.view_count.desc(), Design.id.desc()), (Design.view_count, Design.id)
    return (Design.created_at.desc(), Design.id.desc()), (Design.created_at, Design.id)


def _cursor_sort_value(design: Design, sort: str) -> str:
    return str(design.view_count) if sort == "trending" else design.created_at.isoformat()


@router.post("", response_model=DesignOut, status_code=201)
def create_design(
    payload: DesignCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_CREATE_ROLES)),
    db: Session = Depends(get_db_session),
) -> DesignOut:
    artist_profile_id: uuid.UUID | None = None
    if current.effective_role not in _EDIT_STAFF_ROLES:
        artist_profile = db.execute(
            select(ArtistProfile).where(ArtistProfile.user_id == current.user.id)
        ).scalar_one_or_none()
        if artist_profile is None:
            raise AppError("You need an artist profile before creating designs.", status_code=422)
        artist_profile_id = artist_profile.id

    if payload.is_premium and current.effective_role not in _PREMIUM_ROLES:
        raise AuthorizationError("Only verified artists can mark a design as premium.")

    design = Design(
        artist_profile_id=artist_profile_id,
        title=payload.title,
        description=payload.description,
        difficulty_level=payload.difficulty_level,
        body_placement=payload.body_placement,
        is_premium=payload.is_premium,
    )
    db.add(design)
    db.flush()

    _sync_categories(db, design.id, payload.category_ids)
    _sync_tags(db, design.id, payload.tag_names)

    db.commit()
    db.refresh(design)
    return _design_out(db, design, include_non_ready_images=True, current_user_id=current.user.id)


@router.get("/home-feed", response_model=HomeFeedOut)
def get_home_feed(
    response: Response,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> HomeFeedOut:
    base = select(Design).where(
        Design.status == DesignStatus.PUBLISHED.value, Design.deleted_at.is_(None)
    )

    latest = list(
        db.execute(
            base.order_by(Design.created_at.desc(), Design.id.desc()).limit(
                _HOME_FEED_SECTION_LIMIT
            )
        )
        .scalars()
        .all()
    )
    featured = list(
        db.execute(
            base.where(Design.is_featured.is_(True))
            .order_by(Design.created_at.desc(), Design.id.desc())
            .limit(_HOME_FEED_SECTION_LIMIT)
        )
        .scalars()
        .all()
    )
    trending = list(
        db.execute(
            base.order_by(Design.view_count.desc(), Design.id.desc()).limit(
                _HOME_FEED_SECTION_LIMIT
            )
        )
        .scalars()
        .all()
    )

    # Batch image/artist lookups once across the union of all three
    # sections — see docs/design-gallery.md#query-optimization.
    union_by_id = {d.id: d for d in [*latest, *featured, *trending]}
    union_ids = list(union_by_id.keys())
    union_artist_ids = [
        d.artist_profile_id for d in union_by_id.values() if d.artist_profile_id is not None
    ]
    images_by_design = batch_primary_images(db, union_ids)
    artists_by_profile = batch_artist_summaries(db, union_artist_ids)

    def _to_summaries(designs: list[Design]) -> list[DesignSummaryOut]:
        return [
            design_summary_out(
                d,
                primary_image=images_by_design.get(d.id),
                artist=(
                    artists_by_profile.get(d.artist_profile_id) if d.artist_profile_id else None
                ),
            )
            for d in designs
        ]

    set_public_cache(response, max_age_seconds=60)
    return HomeFeedOut(
        latest=_to_summaries(latest),
        featured=_to_summaries(featured),
        trending=_to_summaries(trending),
    )


@router.get("/published", response_model=DesignListOut)
def list_published_designs(
    response: Response,
    category_id: uuid.UUID | None = None,
    difficulty_level: str | None = None,
    body_placement: str | None = None,
    artist_profile_id: uuid.UUID | None = None,
    sort: str = "latest",
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignListOut:
    if sort not in _SORT_MODES:
        raise AppError(f"sort must be one of: {', '.join(sorted(_SORT_MODES))}", status_code=422)
    limit = max(1, min(limit, 100))

    stmt = select(Design).where(
        Design.status == DesignStatus.PUBLISHED.value, Design.deleted_at.is_(None)
    )
    if difficulty_level is not None:
        stmt = stmt.where(Design.difficulty_level == difficulty_level)
    if body_placement is not None:
        stmt = stmt.where(Design.body_placement == body_placement)
    if artist_profile_id is not None:
        # Powers an artist's full, paginated public portfolio (see
        # docs/artist-directory.md#full-portfolio-reuses-designs-published) —
        # the profile endpoint itself only returns a preview.
        stmt = stmt.where(Design.artist_profile_id == artist_profile_id)
    if category_id is not None:
        stmt = stmt.join(DesignCategory, DesignCategory.design_id == Design.id).where(
            DesignCategory.category_id == category_id
        )

    order_cols, cursor_cols = _order_and_cursor_columns(sort)
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=sort)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_value: datetime | int = (
            int(decoded.sort_value)
            if sort == "trending"
            else datetime.fromisoformat(decoded.sort_value)
        )
        stmt = stmt.where(tuple_(*cursor_cols) < tuple_(literal(cursor_value), literal(decoded.id)))

    stmt = stmt.order_by(*order_cols).limit(limit + 1)

    designs = list(db.execute(stmt).scalars().all())
    has_more = len(designs) > limit
    page = designs[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=sort, sort_value=_cursor_sort_value(last, sort), id_=last.id
        )

    set_public_cache(response, max_age_seconds=30)
    return DesignListOut(
        items=summaries_for_designs(db, page),
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/mine", response_model=DesignListOut)
def list_my_designs(
    response: Response,
    status_filter: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignListOut:
    """The artist's own portfolio-management listing — every status
    (draft/published/archived/flagged), not just published. See
    docs/artist-directory.md#portfolio-management-listing. Distinct from
    `GET /designs/published?artist_profile_id=...`, which is the public,
    published-only view of a specific artist's portfolio."""
    artist_profile = db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == current.user.id)
    ).scalar_one_or_none()
    if artist_profile is None:
        raise AppError("You need an artist profile before viewing your portfolio.", status_code=404)

    limit = max(1, min(limit, 100))
    valid_statuses = {member.value for member in DesignStatus}
    if status_filter is not None and status_filter not in valid_statuses:
        raise AppError(
            f"status_filter must be one of: {', '.join(sorted(valid_statuses))}", status_code=422
        )

    stmt = select(Design).where(
        Design.artist_profile_id == artist_profile.id, Design.deleted_at.is_(None)
    )
    if status_filter is not None:
        stmt = stmt.where(Design.status == status_filter)

    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort="mine")
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(Design.created_at, Design.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(Design.created_at.desc(), Design.id.desc()).limit(limit + 1)

    designs = list(db.execute(stmt).scalars().all())
    has_more = len(designs) > limit
    page = designs[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort="mine", sort_value=last.created_at.isoformat(), id_=last.id
        )

    return DesignListOut(
        items=summaries_for_designs(db, page),
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{design_id}", response_model=DesignOut)
def get_design(
    design_id: uuid.UUID,
    response: Response,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignOut:
    design = _get_design_or_404(db, design_id)
    can_view_unpublished = _require_visible(db, design, current)

    if design.status == DesignStatus.PUBLISHED.value:
        set_public_cache(response, max_age_seconds=60)

    # Owner/staff always see full images regardless of premium lock; anyone
    # else needs `premium_design_access` on their current plan — see
    # docs/subscriptions-and-entitlements.md#premium-design-access.
    viewer_has_premium_access = can_view_unpublished
    if not viewer_has_premium_access and design.is_premium:
        features = get_effective_features(db, current.user)
        viewer_has_premium_access = bool(features.get("premium_design_access", False))

    return _design_out(
        db,
        design,
        include_non_ready_images=can_view_unpublished,
        current_user_id=current.user.id,
        viewer_has_premium_access=viewer_has_premium_access,
    )


@router.post("/{design_id}/download", response_model=DesignDownloadOut)
def download_design(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignDownloadOut:
    """Downloading — unlike browsing the detail page — always requires
    premium access for a premium design *and* consumes one unit of the
    caller's monthly download quota (every design, premium or not, counts
    against it). See docs/subscriptions-and-entitlements.md#download-
    limits."""
    design = _get_design_or_404(db, design_id)
    can_view_unpublished = _require_visible(db, design, current)

    if design.is_premium and not can_view_unpublished:
        features = get_effective_features(db, current.user)
        if not features.get("premium_design_access", False):
            raise AppError("This design is only available to premium subscribers.", status_code=403)

    check_and_increment_usage(
        db,
        user=current.user,
        usage_type=UsageType.DESIGN_DOWNLOAD.value,
        limit_key="download_limit_per_month",
    )

    primary_image = (
        db.execute(
            select(DesignImage)
            .where(
                DesignImage.design_id == design.id,
                DesignImage.status == DesignImageStatus.READY.value,
                DesignImage.image_url.is_not(None),
            )
            .order_by(DesignImage.is_primary.desc(), DesignImage.sort_order)
        )
        .scalars()
        .first()
    )
    if primary_image is None or primary_image.image_url is None:
        raise AppError("This design has no downloadable image yet.", status_code=422)

    db.commit()
    return DesignDownloadOut(design_id=design.id, image_url=primary_image.image_url)


@router.get("/{design_id}/related", response_model=list[DesignSummaryOut])
def get_related_designs(
    design_id: uuid.UUID,
    response: Response,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[DesignSummaryOut]:
    design = _get_design_or_404(db, design_id)
    _require_visible(db, design, current)

    category_ids = (
        db.execute(select(DesignCategory.category_id).where(DesignCategory.design_id == design_id))
        .scalars()
        .all()
    )

    related: list[Design] = []
    if category_ids:
        related = list(
            db.execute(
                select(Design)
                .join(DesignCategory, DesignCategory.design_id == Design.id)
                .where(
                    DesignCategory.category_id.in_(category_ids),
                    Design.status == DesignStatus.PUBLISHED.value,
                    Design.id != design_id,
                    Design.deleted_at.is_(None),
                )
                .distinct()
                .order_by(Design.created_at.desc(), Design.id.desc())
                .limit(_RELATED_DESIGNS_LIMIT)
            )
            .scalars()
            .all()
        )

    set_public_cache(response, max_age_seconds=60)
    return summaries_for_designs(db, related)


@router.patch("/{design_id}", response_model=DesignOut)
def update_design(
    design_id: uuid.UUID,
    payload: DesignUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignOut:
    design = _get_design_or_404(db, design_id)
    _require_edit_permission(db, design, current)

    updates = payload.model_dump(exclude_unset=True)
    category_ids = updates.pop("category_ids", None)
    tag_names = updates.pop("tag_names", None)
    new_status = updates.pop("status", None)

    if updates.get("is_premium") and current.effective_role not in _PREMIUM_ROLES:
        raise AuthorizationError("Only verified artists can mark a design as premium.")

    if new_status is not None and new_status != design.status:
        if not is_valid_owner_design_transition(design.status, new_status):
            raise AppError(
                f"Cannot move a design from '{design.status}' to '{new_status}'.", status_code=422
            )
        if new_status == DesignStatus.PUBLISHED.value and design.artist_profile_id is not None:
            owner_user_id = _owning_user_id(db, design, current)
            owner_user = db.get(User, owner_user_id)
            if owner_user is not None:
                published_count = db.execute(
                    select(func.count())
                    .select_from(Design)
                    .where(
                        Design.artist_profile_id == design.artist_profile_id,
                        Design.status == DesignStatus.PUBLISHED.value,
                        Design.deleted_at.is_(None),
                    )
                ).scalar_one()
                require_portfolio_capacity(db, owner_user, current_design_count=published_count)
        design.status = new_status

    for field, value in updates.items():
        setattr(design, field, value)

    if category_ids is not None:
        _sync_categories(db, design.id, category_ids)
    if tag_names is not None:
        _sync_tags(db, design.id, tag_names)

    db.add(design)
    db.commit()
    db.refresh(design)
    return _design_out(db, design, include_non_ready_images=True, current_user_id=current.user.id)


@router.post("/{design_id}/archive", response_model=DesignOut)
def archive_design(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignOut:
    design = _get_design_or_404(db, design_id)
    _require_edit_permission(db, design, current)

    if design.status not in DESIGN_ARCHIVABLE_STATUSES:
        raise AppError(f"Cannot archive a design with status '{design.status}'.", status_code=422)

    design.status = DesignStatus.ARCHIVED.value
    db.add(design)
    db.commit()
    db.refresh(design)
    return _design_out(db, design, include_non_ready_images=True, current_user_id=current.user.id)


@router.post("/{design_id}/view", status_code=204)
def record_design_view_event(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    design = _get_design_or_404(db, design_id)
    if design.status != DesignStatus.PUBLISHED.value:
        # Viewing your own draft (or a staff preview) is not a public view —
        # see docs/design-gallery.md#view-count-event-handling.
        return
    record_design_view(db, design_id=design_id, viewer_id=current.user.id)


@router.post(
    "/{design_id}/images/authorize", response_model=DesignImageAuthorizeResponse, status_code=201
)
def authorize_design_image_upload(
    design_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignImageAuthorizeResponse:
    design = _get_design_or_404(db, design_id)
    _require_edit_permission(db, design, current)

    next_sort_order = (
        db.execute(
            select(func.coalesce(func.max(DesignImage.sort_order), -1)).where(
                DesignImage.design_id == design_id
            )
        ).scalar_one()
        + 1
    )

    image = DesignImage(
        design_id=design_id, sort_order=next_sort_order, status=DesignImageStatus.PENDING.value
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return DesignImageAuthorizeResponse(
        image_id=image.id,
        max_file_size_bytes=MAX_DESIGN_IMAGE_BYTES,
        allowed_content_types=sorted(ALLOWED_CONTENT_TYPES),
    )


@router.post("/{design_id}/images/{image_id}/upload", response_model=DesignImageOut)
async def upload_design_image(
    design_id: uuid.UUID,
    image_id: uuid.UUID,
    file: UploadFile,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DesignImageOut:
    design = _get_design_or_404(db, design_id)
    _require_edit_permission(db, design, current)

    image = db.get(DesignImage, image_id)
    if image is None or image.design_id != design_id:
        raise AppError("Image upload was not authorized for this design.", status_code=404)
    if image.status != DesignImageStatus.PENDING.value:
        raise AppError("This image has already been uploaded.", status_code=409)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise AppError("Unsupported image type. Use JPEG, PNG, or WEBP.", status_code=422)

    raw = await file.read()
    try:
        processed = process_image_upload(raw, max_bytes=MAX_DESIGN_IMAGE_BYTES)
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc

    # Step 4 of docs/design-catalog.md#image-upload-pipeline: record the
    # upload before processing (thumbnailing) begins.
    image.original_filename = file.filename
    image.mime_type = processed.content_type
    image.file_size_bytes = len(raw)
    image.checksum_sha256 = processed.checksum_sha256
    image.width = processed.width
    image.height = processed.height
    image.uploaded_by = current.user.id
    image.storage_path = storage_prefix(
        artist_user_id=_owning_user_id(db, design, current), design_id=design_id, image_id=image_id
    )
    db.add(image)
    db.commit()

    # Steps 5-8: queue (synchronous in this phase) processing, thumbnails,
    # dimensions, and the final `ready` transition.
    queue_image_processing(db, design_image=image, processed=processed, prefix=image.storage_path)
    db.refresh(image)

    if image.status == DesignImageStatus.READY.value:
        _queue_ai_jobs_for_new_image(db, design)
        db.commit()

    return _design_image_out(image, premium_locked=False)
