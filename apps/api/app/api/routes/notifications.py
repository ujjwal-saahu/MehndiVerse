"""In-app notification history — see docs/booking-messaging.md#3-notifications.

Notification *preferences* (email/push/sms toggles) already exist —
`GET/PATCH /users/me/preferences`, Phase 4/5 — this router is only the
read-side history/inbox for notifications already created by
app/services/notifications.py::notify_user().
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, literal, select, tuple_, update
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError, AuthorizationError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.models.notification import Notification
from app.db.session import get_db_session
from app.schemas.design import PageInfo
from app.schemas.notification import NotificationListOut, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])

_SORT = "notifications"
_PAGE_SIZE = 30


def _out(notification: Notification) -> NotificationOut:
    return NotificationOut(
        id=notification.id,
        type=notification.type,
        channel=notification.channel,
        title=notification.title,
        body=notification.body,
        data=notification.data,
        is_read=notification.is_read,
        read_at=notification.read_at,
        sent_at=notification.sent_at,
        created_at=notification.created_at,
    )


def _unread_count(db: Session, user_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
    ).scalar_one()


@router.get("", response_model=NotificationListOut)
def list_my_notifications(
    cursor: str | None = None,
    unread_only: bool = False,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> NotificationListOut:
    stmt = select(Notification).where(
        Notification.user_id == current.user.id, Notification.deleted_at.is_(None)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(Notification.created_at, Notification.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(
        _PAGE_SIZE + 1
    )

    notifications = list(db.execute(stmt).scalars().all())
    has_more = len(notifications) > _PAGE_SIZE
    page = notifications[:_PAGE_SIZE]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(sort=_SORT, sort_value=last.created_at.isoformat(), id_=last.id)

    return NotificationListOut(
        items=[_out(n) for n in page],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
        unread_count=_unread_count(db, current.user.id),
    )


@router.get("/unread-count")
def get_unread_notification_count(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict[str, int]:
    return {"unread_count": _unread_count(db, current.user.id)}


@router.post("/read-all", status_code=204)
def mark_all_notifications_read(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    now = datetime.now(UTC)
    db.execute(
        update(Notification)
        .where(Notification.user_id == current.user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    db.commit()


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> NotificationOut:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.deleted_at is not None:
        raise AppError("Notification not found.", status_code=404)
    if notification.user_id != current.user.id:
        raise AuthorizationError("You do not have access to this notification.")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        db.add(notification)
        db.commit()
        db.refresh(notification)
    return _out(notification)
