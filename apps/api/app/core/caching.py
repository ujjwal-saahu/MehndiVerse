"""Safe caching foundation for public gallery responses — see
docs/design-gallery.md#safe-caching-foundation.

`set_public_cache` must only ever be called on a response that is safe for a
shared cache (a CDN, a corporate proxy, another visitor's browser) to reuse
for *any* requester — never on a response whose contents depend on who's
asking. Concretely: it's safe on list/section endpoints (they only ever
return published designs, identical for everyone), and on a single design's
detail endpoint *only* when that design is actually published — an owner or
moderator viewing their own draft must never have that response cached and
replayed to someone else.
"""

from fastapi import Response


def set_public_cache(response: Response, *, max_age_seconds: int) -> None:
    response.headers["Cache-Control"] = f"public, max-age={max_age_seconds}"
