import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.design import PageInfo


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    channel: str
    title: str
    body: str
    data: dict[str, Any] | None
    is_read: bool
    read_at: datetime | None
    sent_at: datetime | None
    created_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    page_info: PageInfo
    unread_count: int
