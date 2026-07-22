"""Self-service data export — see docs/legal-and-support.md#data-export-
request. Generated synchronously and returned directly; nothing is emailed
or stored (see app/services/legal.py::build_account_data_export's
docstring for why)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.db.session import get_db_session
from app.schemas.legal import AccountDataExportOut
from app.services.legal import build_account_data_export

router = APIRouter(prefix="/account", tags=["legal"])


@router.get("/data-export", response_model=AccountDataExportOut)
def export_my_data(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AccountDataExportOut:
    payload = build_account_data_export(db, user=current.user)
    db.commit()
    return AccountDataExportOut(**payload)
