"""Account-based login-abuse protection — see docs/security-review.md
#login-abuse-protection.

`auth_rate_limit` (app/api/deps.py's slowapi limiter) already throttles the
`/auth/login` endpoint *by IP*, which stops a single source from hammering
the endpoint but does nothing against credential stuffing spread across
many IPs against one account. This module adds a second, account-keyed
counter on top: after `login_lockout_threshold` failed attempts for the
same email within `login_lockout_window_seconds`, further attempts for
that email are rejected before Supabase is even called, regardless of
which IP they come from.

Keyed by a hash of the normalized email, never the raw address, so a Redis
`KEYS`/`SCAN` or an operator glancing at Redis never sees a plaintext email
list of who's being targeted.
"""

import hashlib

from app.core.config import get_settings
from app.core.redis_client import get_redis_client

_KEY_PREFIX = "login_fail"


def _key(email: str) -> str:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return f"{_KEY_PREFIX}:{digest}"


def is_locked_out(email: str) -> bool:
    settings = get_settings()
    count = get_redis_client().get(_key(email))
    return count is not None and int(count) >= settings.login_lockout_threshold


def record_failed_login(email: str) -> int:
    """Increments the failure counter and (re)sets its expiry, returning the
    new count. The window slides on every failure — a burst of attempts
    keeps the account locked rather than the lockout silently expiring
    mid-attack."""
    settings = get_settings()
    client = get_redis_client()
    key = _key(email)
    count = client.incr(key)
    client.expire(key, settings.login_lockout_window_seconds)
    return int(count)


def clear_failed_logins(email: str) -> None:
    get_redis_client().delete(_key(email))
