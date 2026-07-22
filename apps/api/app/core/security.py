"""Local verification of Supabase-issued access tokens.

No network call to Supabase is needed to authenticate a request — Supabase
access tokens are JWTs signed with the project's JWT secret (HS256), so we
verify the signature and claims locally. See docs/authentication.md#2.

IMPORTANT: the JWT's own `role` claim is Supabase's Postgres-role selector
(`authenticated` / `anon`), used by Supabase for its own RLS evaluation — it is
NOT the application role and must never be used for authorization decisions.
The application role always comes from the `users` table, looked up by `sub`.
"""

import uuid
from dataclasses import dataclass

import jwt

from app.core.config import get_settings


class InvalidTokenError(Exception):
    """A token failed signature, audience, or expiry verification."""


@dataclass(frozen=True)
class TokenPayload:
    user_id: uuid.UUID
    email: str | None


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc

    subject = claims.get("sub")
    if not subject:
        raise InvalidTokenError("Access token is missing a subject claim.")

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError("Access token subject is not a valid user id.") from exc

    return TokenPayload(user_id=user_id, email=claims.get("email"))
