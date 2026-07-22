"""Search-input sanitization — see docs/design-search.md#sanitize-search-inputs.

This isn't about SQL injection (SQLAlchemy parameterizes every value it
sends, and `websearch_to_tsquery` — see postgres_provider.py — is designed
specifically to accept raw, untrusted user text safely). It's about not
handing Postgres's full-text parser degenerate input: control characters, a
query that's only whitespace, or an unbounded-length string that costs work
for no useful result. See also "prevent expensive uncontrolled queries" in
the same doc for the query-length/limit clamps this pairs with.
"""

import re

MAX_QUERY_LENGTH = 200

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_search_query(raw: str | None) -> str | None:
    """Returns a cleaned, length-capped query string, or `None` if nothing
    meaningful is left to search for once cleaned."""
    if raw is None:
        return None
    cleaned = _CONTROL_CHARS_RE.sub("", raw)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if not cleaned:
        return None
    return cleaned[:MAX_QUERY_LENGTH]
