"""Report-a-problem / contact-support submissions — see docs/legal-and-
support.md#report-a-problem-and-contact-support. Usable signed-out (a
visitor hitting a bug before they can even log in still needs to report
it), so `current` is optional; a rate limit keyed by remote address guards
against anonymous spam the same way app/api/routes/reports.py does."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user_optional, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.enums import SupportRequestCategory
from app.db.session import get_db_session
from app.schemas.legal import SupportRequestCreate, SupportRequestOut
from app.services.legal import create_support_request

router = APIRouter(tags=["support"])

_VALID_CATEGORIES = {member.value for member in SupportRequestCategory}


def _rate_limit() -> str:
    return get_settings().support_request_rate_limit


@router.post("/support/requests", response_model=SupportRequestOut, status_code=201)
@limiter.limit(_rate_limit())
def submit_support_request(
    request: Request,
    payload: SupportRequestCreate,
    current: AuthenticatedUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db_session),
) -> SupportRequestOut:
    if payload.category not in _VALID_CATEGORIES:
        raise AppError("Unknown support request category.", status_code=422)

    support_request = create_support_request(
        db,
        user_id=current.user.id if current else None,
        contact_email=payload.contact_email,
        category=payload.category,
        subject=payload.subject,
        message=payload.message,
    )
    db.commit()
    db.refresh(support_request)
    return SupportRequestOut(
        id=support_request.id,
        category=support_request.category,
        subject=support_request.subject,
        status=support_request.status,
        created_at=support_request.created_at,
    )
