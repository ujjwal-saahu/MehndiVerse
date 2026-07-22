"""Public payment-provider webhook endpoint — see
docs/payments.md#5-signed-webhook-handling-and-duplicate-protection.

Deliberately unauthenticated by user session (the provider isn't a logged-in
user) — authenticity instead comes entirely from the signed-payload check in
`handle_webhook()`. This is the only route in the app that reads the raw
request body before any JSON parsing, since signature verification must run
against the exact bytes the provider signed.
"""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.payments.service import handle_webhook

router = APIRouter(prefix="/webhooks/payments", tags=["payment-webhooks"])


@router.post("/razorpay", status_code=200)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db_session),
) -> dict[str, bool]:
    raw_body = await request.body()
    handle_webhook(db, raw_body=raw_body, signature=x_razorpay_signature)
    db.commit()
    return {"ok": True}
