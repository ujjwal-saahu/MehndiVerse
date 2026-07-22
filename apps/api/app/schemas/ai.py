"""Request/response models for the AI foundation — see
docs/ai-foundation.md. `AiGenerationRequest`/`AiGenerationOut` are the
original (Phase 18) quota-gated freeform generation shapes; everything else
here backs the job-queue-driven capabilities added in Phase 20 (tag
suggestion, embeddings/similarity, duplicate detection, moderation, human
review, recommendation events)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.design import DesignSummaryOut, PageInfo


class AiGenerationRequest(BaseModel):
    generation_type: str
    request_payload: dict[str, Any] = Field(default_factory=dict)


class AiGenerationOut(BaseModel):
    id: uuid.UUID
    generation_type: str
    status: str
    response_payload: dict[str, Any] | None
    created_at: datetime


class AiGenerationStatusOut(BaseModel):
    """Polled by a client after triggering a job-backed capability (tag
    suggestion / embedding / moderation / duplicate detection) to learn when
    it finishes — see docs/ai-foundation.md#ai-request-records."""

    id: uuid.UUID
    generation_type: str
    status: str
    provider: str | None
    model_name: str | None
    confidence: float | None
    requires_human_review: bool
    review_status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class TagSuggestionOut(BaseModel):
    id: uuid.UUID
    design_id: uuid.UUID
    tag_name: str
    confidence: float
    status: str
    created_at: datetime


class TagSuggestionResolutionRequest(BaseModel):
    accepted: bool


class SimilarDesignOut(BaseModel):
    design: DesignSummaryOut
    similarity: float


class DuplicateMatchOut(BaseModel):
    id: uuid.UUID
    design_id: uuid.UUID
    matched_design_id: uuid.UUID
    similarity: float
    status: str
    created_at: datetime


class ReviewResolutionRequest(BaseModel):
    approved: bool
    notes: str | None = None


class AiJobOut(BaseModel):
    id: uuid.UUID
    generation_id: uuid.UUID
    job_type: str
    status: str
    attempt_count: int
    max_attempts: int
    last_error: str | None
    next_run_at: datetime
    created_at: datetime


class AiReviewQueueOut(BaseModel):
    items: list[AiGenerationStatusOut]
    page_info: PageInfo


class AiDuplicateQueueOut(BaseModel):
    items: list[DuplicateMatchOut]
    page_info: PageInfo
