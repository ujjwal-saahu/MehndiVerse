"""Artist availability and scheduling — see docs/artist-scheduling.md."""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

_VALID_BLOCK_TYPES = {"holiday", "personal_leave", "vacation", "other"}


class ArtistScheduleSettingsOut(BaseModel):
    timezone: str
    default_buffer_minutes: int
    default_travel_buffer_minutes: int


class ArtistScheduleSettingsUpdateRequest(BaseModel):
    timezone: str | None = Field(default=None, min_length=1, max_length=50)
    default_buffer_minutes: int | None = Field(default=None, ge=0)
    default_travel_buffer_minutes: int | None = Field(default=None, ge=0)


class AvailabilityRuleOut(BaseModel):
    id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    is_active: bool


class AvailabilityRuleCreateRequest(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def _check_range(self) -> "AvailabilityRuleCreateRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class AvailabilityRuleUpdateRequest(BaseModel):
    """Partial update — only fields explicitly present are applied
    (`exclude_unset`). Range consistency is re-checked in the route after
    merging onto the existing row."""

    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


class BlockedDateOut(BaseModel):
    id: UUID
    start_date: date
    end_date: date
    block_type: str
    start_time: time | None
    end_time: time | None
    reason: str | None


class BlockedDateCreateRequest(BaseModel):
    start_date: date
    end_date: date
    block_type: str = "other"
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _check_range(self) -> "BlockedDateCreateRequest":
        if self.block_type not in _VALID_BLOCK_TYPES:
            raise ValueError(f"block_type must be one of: {', '.join(sorted(_VALID_BLOCK_TYPES))}")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("start_time and end_time must be provided together.")
        if self.start_time is not None:
            assert self.end_time is not None
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time.")
            if self.start_date != self.end_date:
                raise ValueError(
                    "A time-scoped block (start_time/end_time set) must be a single day "
                    "(start_date must equal end_date)."
                )
        return self


class BlockedDateUpdateRequest(BaseModel):
    """Partial update — only fields explicitly present are applied
    (`exclude_unset`). Range consistency is re-checked in the route after
    merging onto the existing row."""

    start_date: date | None = None
    end_date: date | None = None
    block_type: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = Field(default=None, max_length=255)


class CalendarWindowOut(BaseModel):
    start_time: time
    end_time: time


class CalendarDayOut(BaseModel):
    date: date
    day_of_week: int
    windows: list[CalendarWindowOut]
    blocks: list[BlockedDateOut]
    is_available: bool


class CalendarViewOut(BaseModel):
    timezone: str
    days: list[CalendarDayOut]


class AvailableSlotOut(BaseModel):
    start: datetime
    end: datetime


class AvailableSlotsOut(BaseModel):
    artist_profile_id: UUID
    service_id: UUID
    artist_timezone: str
    slots: list[AvailableSlotOut]
