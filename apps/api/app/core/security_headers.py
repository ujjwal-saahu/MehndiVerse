"""Security response headers — see docs/security-review.md#security-
headers. A pure JSON API never renders HTML/scripts itself, so the CSP can
be maximally restrictive (`default-src 'none'`) rather than the tradeoffs a
page-serving app has to make."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.core.config import get_settings

_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
_HSTS = "max-age=63072000; includeSubDomains; preload"


def add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def _security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in _HEADERS.items():
            response.headers.setdefault(name, value)
        # HSTS only makes sense once the app is actually served over HTTPS —
        # sending it in local/dev over plain HTTP is a no-op at best and
        # confusing at worst.
        if get_settings().environment == "production":
            response.headers.setdefault("Strict-Transport-Security", _HSTS)
        return response
