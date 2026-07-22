"""Human-review resolution — see docs/ai-foundation.md#human-review."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import AiReviewStatus, DuplicateMatchStatus, TagSuggestionStatus
from app.services.ai.review import (
    resolve_duplicate_match,
    resolve_generation_review,
    resolve_tag_suggestion,
)
from tests.db.factories import (
    make_ai_generation,
    make_design,
    make_duplicate_match,
    make_tag_suggestion,
    make_user,
)


def test_resolve_generation_review_approves_a_pending_result(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    generation = make_ai_generation(db_session)
    generation.requires_human_review = True
    generation.review_status = AiReviewStatus.PENDING.value
    db_session.commit()

    resolve_generation_review(db_session, generation, resolved_by=staff.id, approved=True)
    db_session.commit()

    assert generation.review_status == AiReviewStatus.APPROVED.value
    assert generation.reviewed_by == staff.id
    assert generation.reviewed_at is not None


def test_resolve_generation_review_rejects_a_pending_result(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    generation = make_ai_generation(db_session)
    generation.requires_human_review = True
    generation.review_status = AiReviewStatus.PENDING.value
    db_session.commit()

    resolve_generation_review(
        db_session, generation, resolved_by=staff.id, approved=False, notes="Looks off."
    )
    db_session.commit()

    assert generation.review_status == AiReviewStatus.REJECTED.value
    assert generation.review_notes == "Looks off."


def test_resolve_generation_review_rejects_double_resolution(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    generation = make_ai_generation(db_session)
    generation.review_status = AiReviewStatus.APPROVED.value
    db_session.commit()

    with pytest.raises(AppError):
        resolve_generation_review(db_session, generation, resolved_by=staff.id, approved=True)


def test_resolve_tag_suggestion_accepts(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    design = make_design(db_session)
    suggestion = make_tag_suggestion(db_session, design=design)
    db_session.commit()

    resolve_tag_suggestion(db_session, suggestion, resolved_by=staff.id, accepted=True)
    db_session.commit()

    assert suggestion.status == TagSuggestionStatus.ACCEPTED.value
    assert suggestion.resolved_by == staff.id


def test_resolve_tag_suggestion_rejects_double_resolution(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    design = make_design(db_session)
    suggestion = make_tag_suggestion(db_session, design=design, status="rejected")
    db_session.commit()

    with pytest.raises(AppError):
        resolve_tag_suggestion(db_session, suggestion, resolved_by=staff.id, accepted=True)


def test_resolve_duplicate_match_confirms(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    design_a = make_design(db_session)
    design_b = make_design(db_session)
    match = make_duplicate_match(db_session, design=design_a, matched_design=design_b)
    db_session.commit()

    resolve_duplicate_match(db_session, match, resolved_by=staff.id, confirmed=True)
    db_session.commit()

    assert match.status == DuplicateMatchStatus.CONFIRMED.value


def test_resolve_duplicate_match_dismisses(db_session: Session) -> None:
    staff = make_user(db_session, role="administrator")
    design_a = make_design(db_session)
    design_b = make_design(db_session)
    match = make_duplicate_match(db_session, design=design_a, matched_design=design_b)
    db_session.commit()

    resolve_duplicate_match(db_session, match, resolved_by=staff.id, confirmed=False)
    db_session.commit()

    assert match.status == DuplicateMatchStatus.DISMISSED.value
