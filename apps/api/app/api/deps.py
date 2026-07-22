"""Shared FastAPI dependencies: DB session, authenticated user, RBAC."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.authz import ALL_EFFECTIVE_ROLES, get_effective_role
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import InvalidTokenError, decode_access_token
from app.db.enums import UserRole
from app.db.models.user import User
from app.db.session import get_db_session

bearer_scheme = HTTPBearer(auto_error=False)

limiter = Limiter(key_func=get_remote_address, storage_uri=get_settings().redis_url)


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    effective_role: str
    access_token: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> AuthenticatedUser:
    if credentials is None:
        raise AuthenticationError("Missing bearer token.")

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AuthenticationError(str(exc)) from exc

    user = db.get(User, payload.user_id)
    if user is None:
        # Token is valid (issued by Supabase for a real auth.users row) but no
        # local profile row exists yet — provision one lazily so a valid
        # token always resolves to a usable account. See docs/authentication.md.
        placeholder_email = payload.email or f"{payload.user_id}@unknown.local"
        user = User(id=payload.user_id, email=placeholder_email, role=UserRole.CUSTOMER.value)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.deleted_at is not None:
        raise AuthenticationError("This account has been deleted.")

    effective_role = get_effective_role(user, db)
    return AuthenticatedUser(
        user=user, effective_role=effective_role, access_token=credentials.credentials
    )


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> AuthenticatedUser | None:
    """Like `get_current_user`, but returns `None` instead of raising when no
    bearer token was sent at all — for endpoints usable by signed-out guests
    (e.g. contact-support) that still attribute the request to an account
    when one is signed in. A *present but invalid* token still raises, same
    as `get_current_user` — silently downgrading a bad token to "guest"
    would hide an expired-session bug or an actual attack."""
    if credentials is None:
        return None
    return get_current_user(credentials=credentials, db=db)


def require_roles(*roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """RBAC dependency factory. `roles` must be effective-role strings (see
    app/core/authz.py) — never derived from anything the client sends."""
    unknown = set(roles) - ALL_EFFECTIVE_ROLES
    if unknown:
        raise ValueError(f"Unknown effective role(s) in require_roles(): {unknown}")

    def _dependency(current: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current.effective_role not in roles:
            raise AuthorizationError(f"This action requires one of: {', '.join(sorted(roles))}.")
        return current

    return _dependency
