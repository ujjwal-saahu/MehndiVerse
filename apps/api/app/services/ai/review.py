"""Human-review resolution — see docs/ai-foundation.md#human-review.

`resolve_generation_review` closes out an `AiGeneration.review_status` of
`pending` (set by `moderation.py` on a flagged/uncertain result, or by
`duplicates.py` when a match is found) — mirrors
`app/services/reports.py::resolve_report`/`dismiss_report`'s exact shape:
validate the current state is still open, stamp who/when/why, never allow
double-resolution.

`resolve_tag_suggestion` and `resolve_duplicate_match` are the same
"human decides" discipline applied to the two other things this package
asks a person to look at, but they resolve their own status column
directly rather than through `AiGeneration.review_status` — accepting a
tag suggestion is a product action (apply or don't), not a moderation
verdict, and a duplicate match's `confirmed`/`dismissed` status is what
staff actually act on.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import AiReviewStatus, DuplicateMatchStatus, TagSuggestionStatus
from app.db.models.ai import AiGeneration, DesignDuplicateMatch, DesignTagSuggestion


def resolve_generation_review(
    db: Session,
    generation: AiGeneration,
    *,
    resolved_by: uuid.UUID,
    approved: bool,
    notes: str | None = None,
) -> None:
    if generation.review_status != AiReviewStatus.PENDING.value:
        raise AppError("This AI result has already been reviewed.", status_code=422)
    generation.review_status = (
        AiReviewStatus.APPROVED.value if approved else AiReviewStatus.REJECTED.value
    )
    generation.reviewed_by = resolved_by
    generation.reviewed_at = datetime.now(UTC)
    generation.review_notes = notes
    db.add(generation)


def resolve_tag_suggestion(
    db: Session, suggestion: DesignTagSuggestion, *, resolved_by: uuid.UUID, accepted: bool
) -> None:
    if suggestion.status != TagSuggestionStatus.PENDING.value:
        raise AppError("This tag suggestion has already been resolved.", status_code=422)
    suggestion.status = (
        TagSuggestionStatus.ACCEPTED.value if accepted else TagSuggestionStatus.REJECTED.value
    )
    suggestion.resolved_by = resolved_by
    suggestion.resolved_at = datetime.now(UTC)
    db.add(suggestion)


def resolve_duplicate_match(
    db: Session, match: DesignDuplicateMatch, *, resolved_by: uuid.UUID, confirmed: bool
) -> None:
    if match.status != DuplicateMatchStatus.PENDING.value:
        raise AppError("This duplicate match has already been resolved.", status_code=422)
    match.status = (
        DuplicateMatchStatus.CONFIRMED.value if confirmed else DuplicateMatchStatus.DISMISSED.value
    )
    match.resolved_by = resolved_by
    match.resolved_at = datetime.now(UTC)
    db.add(match)
