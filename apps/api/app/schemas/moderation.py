"""Request/response models for reporting and the staff moderation queue —
see docs/community-and-trust.md#5-reports-enter-a-moderation-queue."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.design import PageInfo


class ReportCreateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReportOut(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID
    reported_entity_type: str
    reported_entity_id: uuid.UUID
    status: str
    reason: str
    resolution_notes: str | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    created_at: datetime


class ReportQueueItemOut(ReportOut):
    entity_snapshot: dict[str, Any] | None


class ReportQueueOut(BaseModel):
    items: list[ReportQueueItemOut]
    page_info: PageInfo


class ReportResolutionRequest(BaseModel):
    # Mandatory — see docs/admin-dashboard.md#mandatory-reasons (Phase 17
    # tightened this from optional to required; every other moderation
    # action in the admin dashboard already requires one).
    resolution_notes: str = Field(min_length=1, max_length=2000)
