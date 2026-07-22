"""Shared, batched `DesignSummaryOut` construction — used by both
`app/api/routes/designs.py` (home feed, published listing, related designs)
and `app/api/routes/search.py`, so search results render identically to
every other grid in the app and the N+1-avoidance batching (see
docs/design-gallery.md#query-optimization) isn't duplicated.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import DesignImageStatus
from app.db.models.artist import ArtistProfile
from app.db.models.design import Design, DesignImage
from app.db.models.user import Profile
from app.schemas.design import ArtistSummaryOut, DesignSummaryOut


def batch_primary_images(db: Session, design_ids: list[uuid.UUID]) -> dict[uuid.UUID, DesignImage]:
    """One query for however many designs are being summarized, instead of
    one query per design."""
    if not design_ids:
        return {}
    rows = db.execute(
        select(DesignImage)
        .where(
            DesignImage.design_id.in_(design_ids),
            DesignImage.status == DesignImageStatus.READY.value,
        )
        .order_by(DesignImage.design_id, DesignImage.is_primary.desc(), DesignImage.sort_order)
    ).scalars()
    primary_by_design: dict[uuid.UUID, DesignImage] = {}
    for image in rows:
        primary_by_design.setdefault(image.design_id, image)
    return primary_by_design


def batch_artist_summaries(
    db: Session, artist_profile_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ArtistSummaryOut]:
    if not artist_profile_ids:
        return {}
    rows = db.execute(
        select(ArtistProfile, Profile)
        .outerjoin(Profile, Profile.user_id == ArtistProfile.user_id)
        .where(ArtistProfile.id.in_(artist_profile_ids))
    ).all()
    summaries: dict[uuid.UUID, ArtistSummaryOut] = {}
    for artist_profile, profile in rows:
        summaries[artist_profile.id] = ArtistSummaryOut(
            id=artist_profile.id,
            display_name=(
                artist_profile.business_name
                or (profile.display_name if profile else None)
                or "Independent Artist"
            ),
            avatar_url=profile.avatar_url if profile else None,
            headline=artist_profile.headline,
            rating_average=float(artist_profile.rating_average),
            rating_count=artist_profile.rating_count,
            is_accepting_bookings=artist_profile.is_accepting_bookings,
        )
    return summaries


def thumbnail_url(image: DesignImage | None) -> str | None:
    """Grid contexts always prefer the medium thumbnail over the
    full-resolution original — see docs/design-gallery.md#thumbnail-selection."""
    if image is None:
        return None
    return image.thumbnail_medium_url or image.image_url


def design_summary_out(
    design: Design, *, primary_image: DesignImage | None, artist: ArtistSummaryOut | None
) -> DesignSummaryOut:
    return DesignSummaryOut(
        id=design.id,
        artist_profile_id=design.artist_profile_id,
        artist_display_name=artist.display_name if artist else None,
        title=design.title,
        status=design.status,
        is_featured=design.is_featured,
        is_premium=design.is_premium,
        difficulty_level=design.difficulty_level,
        body_placement=design.body_placement,
        thumbnail_url=thumbnail_url(primary_image),
        view_count=design.view_count,
        like_count=design.like_count,
        save_count=design.save_count,
        created_at=design.created_at,
    )


def summaries_for_designs(db: Session, designs: list[Design]) -> list[DesignSummaryOut]:
    """Batched — one query for images, one for artists, regardless of how
    many designs are being summarized."""
    design_ids = [d.id for d in designs]
    artist_profile_ids = [d.artist_profile_id for d in designs if d.artist_profile_id is not None]
    images_by_design = batch_primary_images(db, design_ids)
    artists_by_profile = batch_artist_summaries(db, artist_profile_ids)
    return [
        design_summary_out(
            design,
            primary_image=images_by_design.get(design.id),
            artist=(
                artists_by_profile.get(design.artist_profile_id)
                if design.artist_profile_id
                else None
            ),
        )
        for design in designs
    ]
