"""Self-service artist availability/scheduling management — see
docs/artist-scheduling.md.

Open to any `artist`/`verified_artist` (not gated on verification status),
mirroring app/api/routes/artist_services.py's precedent — an artist can set
up their calendar before their application is approved.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, AuthorizationError
from app.db.models.artist import ArtistAvailability, ArtistBlockedDate, ArtistProfile
from app.db.session import get_db_session
from app.schemas.scheduling import (
    ArtistScheduleSettingsOut,
    ArtistScheduleSettingsUpdateRequest,
    AvailabilityRuleCreateRequest,
    AvailabilityRuleOut,
    AvailabilityRuleUpdateRequest,
    BlockedDateCreateRequest,
    BlockedDateOut,
    BlockedDateUpdateRequest,
    CalendarViewOut,
)
from app.services.scheduling import find_overlapping_block, find_overlapping_rule, validate_timezone
from app.services.scheduling_calendar import build_calendar_view

router = APIRouter(prefix="/artist/availability", tags=["artist-scheduling"])

_SCHEDULING_ROLES = ("artist", "verified_artist")
_MAX_CALENDAR_RANGE_DAYS = 60


def _get_own_profile_or_404(db: Session, current: AuthenticatedUser) -> ArtistProfile:
    profile = db.execute(
        select(ArtistProfile).where(
            ArtistProfile.user_id == current.user.id, ArtistProfile.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("You need an artist profile before managing availability.", status_code=404)
    return profile


def _rule_out(rule: ArtistAvailability) -> AvailabilityRuleOut:
    return AvailabilityRuleOut(
        id=rule.id,
        day_of_week=rule.day_of_week,
        start_time=rule.start_time,
        end_time=rule.end_time,
        is_active=rule.is_active,
    )


def _block_out(block: ArtistBlockedDate) -> BlockedDateOut:
    return BlockedDateOut(
        id=block.id,
        start_date=block.start_date,
        end_date=block.end_date,
        block_type=block.block_type,
        start_time=block.start_time,
        end_time=block.end_time,
        reason=block.reason,
    )


def _get_own_rule_or_404(
    db: Session, rule_id: uuid.UUID, profile: ArtistProfile
) -> ArtistAvailability:
    rule = db.get(ArtistAvailability, rule_id)
    if rule is None:
        raise AppError("Availability rule not found.", status_code=404)
    if rule.artist_profile_id != profile.id:
        raise AuthorizationError("You do not own this availability rule.")
    return rule


def _get_own_block_or_404(
    db: Session, block_id: uuid.UUID, profile: ArtistProfile
) -> ArtistBlockedDate:
    block = db.get(ArtistBlockedDate, block_id)
    if block is None:
        raise AppError("Blocked date not found.", status_code=404)
    if block.artist_profile_id != profile.id:
        raise AuthorizationError("You do not own this blocked date.")
    return block


# --- Settings -----------------------------------------------------------------


@router.get("/settings", response_model=ArtistScheduleSettingsOut)
def get_my_schedule_settings(
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistScheduleSettingsOut:
    profile = _get_own_profile_or_404(db, current)
    return ArtistScheduleSettingsOut(
        timezone=profile.timezone,
        default_buffer_minutes=profile.default_buffer_minutes,
        default_travel_buffer_minutes=profile.default_travel_buffer_minutes,
    )


@router.patch("/settings", response_model=ArtistScheduleSettingsOut)
def update_my_schedule_settings(
    payload: ArtistScheduleSettingsUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> ArtistScheduleSettingsOut:
    profile = _get_own_profile_or_404(db, current)
    updates = payload.model_dump(exclude_unset=True)
    if "timezone" in updates:
        updates["timezone"] = validate_timezone(updates["timezone"])
    for field, value in updates.items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return ArtistScheduleSettingsOut(
        timezone=profile.timezone,
        default_buffer_minutes=profile.default_buffer_minutes,
        default_travel_buffer_minutes=profile.default_travel_buffer_minutes,
    )


# --- Weekly availability rules --------------------------------------------------


@router.get("/rules", response_model=list[AvailabilityRuleOut])
def list_my_availability_rules(
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[AvailabilityRuleOut]:
    profile = _get_own_profile_or_404(db, current)
    rules = (
        db.execute(
            select(ArtistAvailability)
            .where(ArtistAvailability.artist_profile_id == profile.id)
            .order_by(ArtistAvailability.day_of_week, ArtistAvailability.start_time)
        )
        .scalars()
        .all()
    )
    return [_rule_out(r) for r in rules]


@router.post("/rules", response_model=AvailabilityRuleOut, status_code=201)
def create_my_availability_rule(
    payload: AvailabilityRuleCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> AvailabilityRuleOut:
    profile = _get_own_profile_or_404(db, current)
    if find_overlapping_rule(
        db,
        artist_profile_id=profile.id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
    ):
        raise AppError(
            "This overlaps an existing availability rule for the same day.", status_code=409
        )

    rule = ArtistAvailability(
        artist_profile_id=profile.id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_active=payload.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_out(rule)


@router.patch("/rules/{rule_id}", response_model=AvailabilityRuleOut)
def update_my_availability_rule(
    rule_id: uuid.UUID,
    payload: AvailabilityRuleUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> AvailabilityRuleOut:
    profile = _get_own_profile_or_404(db, current)
    rule = _get_own_rule_or_404(db, rule_id, profile)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rule, field, value)

    if rule.end_time <= rule.start_time:
        raise AppError("end_time must be after start_time.", status_code=422)
    if find_overlapping_rule(
        db,
        artist_profile_id=profile.id,
        day_of_week=rule.day_of_week,
        start_time=rule.start_time,
        end_time=rule.end_time,
        exclude_id=rule.id,
    ):
        raise AppError(
            "This overlaps an existing availability rule for the same day.", status_code=409
        )

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_out(rule)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_my_availability_rule(
    rule_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> None:
    profile = _get_own_profile_or_404(db, current)
    rule = _get_own_rule_or_404(db, rule_id, profile)
    db.delete(rule)
    db.commit()


# --- Blocked dates / holidays / leave / manual blocks ----------------------------


@router.get("/blocks", response_model=list[BlockedDateOut])
def list_my_blocked_dates(
    start_date: date | None = None,
    end_date: date | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[BlockedDateOut]:
    profile = _get_own_profile_or_404(db, current)
    stmt = select(ArtistBlockedDate).where(ArtistBlockedDate.artist_profile_id == profile.id)
    if start_date is not None:
        stmt = stmt.where(ArtistBlockedDate.end_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ArtistBlockedDate.start_date <= end_date)
    stmt = stmt.order_by(ArtistBlockedDate.start_date)
    blocks = db.execute(stmt).scalars().all()
    return [_block_out(b) for b in blocks]


@router.post("/blocks", response_model=BlockedDateOut, status_code=201)
def create_my_blocked_date(
    payload: BlockedDateCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> BlockedDateOut:
    profile = _get_own_profile_or_404(db, current)
    if find_overlapping_block(
        db,
        artist_profile_id=profile.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
    ):
        raise AppError("This overlaps an existing blocked date.", status_code=409)

    block = ArtistBlockedDate(
        artist_profile_id=profile.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        block_type=payload.block_type,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return _block_out(block)


@router.patch("/blocks/{block_id}", response_model=BlockedDateOut)
def update_my_blocked_date(
    block_id: uuid.UUID,
    payload: BlockedDateUpdateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> BlockedDateOut:
    profile = _get_own_profile_or_404(db, current)
    block = _get_own_block_or_404(db, block_id, profile)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(block, field, value)

    if block.block_type not in {"holiday", "personal_leave", "vacation", "other"}:
        raise AppError("Unknown block_type.", status_code=422)
    if block.end_date < block.start_date:
        raise AppError("end_date must be on or after start_date.", status_code=422)
    if (block.start_time is None) != (block.end_time is None):
        raise AppError("start_time and end_time must be provided together.", status_code=422)
    if block.start_time is not None:
        assert block.end_time is not None
        if block.end_time <= block.start_time:
            raise AppError("end_time must be after start_time.", status_code=422)
        if block.start_date != block.end_date:
            raise AppError(
                "A time-scoped block must be a single day (start_date must equal end_date).",
                status_code=422,
            )
    if find_overlapping_block(
        db,
        artist_profile_id=profile.id,
        start_date=block.start_date,
        end_date=block.end_date,
        start_time=block.start_time,
        end_time=block.end_time,
        exclude_id=block.id,
    ):
        raise AppError("This overlaps an existing blocked date.", status_code=409)

    db.add(block)
    db.commit()
    db.refresh(block)
    return _block_out(block)


@router.delete("/blocks/{block_id}", status_code=204)
def delete_my_blocked_date(
    block_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> None:
    profile = _get_own_profile_or_404(db, current)
    block = _get_own_block_or_404(db, block_id, profile)
    db.delete(block)
    db.commit()


# --- Calendar view --------------------------------------------------------------


@router.get("/calendar", response_model=CalendarViewOut)
def get_my_calendar(
    start_date: date,
    end_date: date,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> CalendarViewOut:
    profile = _get_own_profile_or_404(db, current)
    if end_date < start_date:
        raise AppError("end_date must be on or after start_date.", status_code=422)
    if (end_date - start_date).days + 1 > _MAX_CALENDAR_RANGE_DAYS:
        raise AppError(
            f"Date range cannot exceed {_MAX_CALENDAR_RANGE_DAYS} days.", status_code=422
        )
    return build_calendar_view(db, profile, start_date=start_date, end_date=end_date)
