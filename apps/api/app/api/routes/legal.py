"""Consent records — see docs/legal-and-support.md#consent-records.
Terms/privacy consent is captured at registration (app/api/routes/
auth.py::register), not here; this router covers the cookie/analytics
consent banner and lets a signed-in user review their own consent
history."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError
from app.db.enums import ConsentType
from app.db.session import get_db_session
from app.schemas.legal import ConsentCreateRequest, ConsentRecordOut
from app.services.legal import list_consent_records, record_consent

router = APIRouter(prefix="/legal", tags=["legal"])

_VALID_CONSENT_TYPES = {member.value for member in ConsentType}


@router.post("/consent", response_model=ConsentRecordOut, status_code=201)
def create_consent(
    payload: ConsentCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ConsentRecordOut:
    if payload.consent_type not in _VALID_CONSENT_TYPES:
        raise AppError("Unknown consent type.", status_code=422)
    record = record_consent(
        db,
        user_id=current.user.id,
        consent_type=payload.consent_type,
        version=payload.version,
        granted=payload.granted,
    )
    db.commit()
    db.refresh(record)
    return ConsentRecordOut(
        id=record.id,
        consent_type=record.consent_type,
        version=record.version,
        granted=record.granted,
        created_at=record.created_at,
    )


@router.get("/consent", response_model=list[ConsentRecordOut])
def get_my_consent(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ConsentRecordOut]:
    records = list_consent_records(db, user_id=current.user.id)
    return [
        ConsentRecordOut(
            id=record.id,
            consent_type=record.consent_type,
            version=record.version,
            granted=record.granted,
            created_at=record.created_at,
        )
        for record in records
    ]
