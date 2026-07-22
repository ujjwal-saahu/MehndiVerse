"""Request/response models for consent, support requests, and the account
data export — see docs/legal-and-support.md."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class ConsentCreateRequest(BaseModel):
    consent_type: str
    version: str = Field(min_length=1, max_length=20)
    granted: bool = True


class ConsentRecordOut(BaseModel):
    id: uuid.UUID
    consent_type: str
    version: str
    granted: bool
    created_at: datetime


class SupportRequestCreate(BaseModel):
    contact_email: EmailStr
    category: str
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)


class SupportRequestOut(BaseModel):
    id: uuid.UUID
    category: str
    subject: str
    status: str
    created_at: datetime


class AccountDataExportOut(BaseModel):
    generated_at: datetime
    profile: dict[str, Any]
    bookings: list[dict[str, Any]]
    payments: list[dict[str, Any]]
    reviews: list[dict[str, Any]]
    consent_records: list[dict[str, Any]]
    support_requests: list[dict[str, Any]]
