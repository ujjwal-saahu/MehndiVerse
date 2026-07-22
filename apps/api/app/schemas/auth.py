from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# NOTE: none of these request schemas accept a `role` field. Registration
# always creates a `customer`; role elevation only happens through the
# dedicated admin endpoint. See docs/authentication.md#3.


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    # Must be explicitly true — see app/core/legal.py and docs/legal-and-
    # support.md#consent-records. Registration itself is the one point every
    # account passes through, so it's the single place terms/privacy consent
    # is captured server-side (not left to a client-side follow-up call).
    terms_accepted: bool = Field(default=False)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    message: str
    session: TokenResponse | None = None


class UserOut(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    created_at: datetime


class RoleUpdateRequest(BaseModel):
    role: str


class AccountDeletionResponse(BaseModel):
    message: str
    deletion_requested_at: datetime


class ReauthRequest(BaseModel):
    """Current password, re-submitted immediately before a privileged action
    (account deletion, revoking all other sessions) — see
    docs/security-review.md#privileged-action-reauthentication."""

    password: str = Field(min_length=1, max_length=72)
