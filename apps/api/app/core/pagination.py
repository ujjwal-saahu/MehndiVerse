"""Cursor (keyset) pagination for the design gallery — see
docs/design-gallery.md#cursor-based-pagination.

Offset pagination (`LIMIT/OFFSET`) gets slower as the offset grows (the
database still has to scan and discard every skipped row) and produces
duplicate/missing items if rows are inserted while a client is paging
through results. Keyset pagination instead remembers the last row's sort key
and asks for "everything strictly after that" — a query the composite
indexes in app/db/models/design.py answer directly, with a cost that doesn't
grow with page depth.

The cursor is opaque to clients (base64) and encodes which `sort` mode
produced it, so a cursor from one sort order is rejected if replayed against
a different one rather than silently producing nonsense results.
"""

import base64
import binascii
import uuid
from dataclasses import dataclass


class InvalidCursorError(Exception):
    """Raised when a cursor is malformed or doesn't match the current sort."""


@dataclass(frozen=True)
class DecodedCursor:
    sort: str
    sort_value: str
    id: uuid.UUID


def encode_cursor(*, sort: str, sort_value: str, id_: uuid.UUID) -> str:
    raw = f"{sort}|{sort_value}|{id_}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str, *, expected_sort: str) -> DecodedCursor:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        sort, sort_value, id_str = raw.split("|", 2)
        parsed_id = uuid.UUID(id_str)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise InvalidCursorError("This pagination cursor is invalid.") from exc

    if sort != expected_sort:
        raise InvalidCursorError("This cursor was issued for a different sort order.")

    return DecodedCursor(sort=sort, sort_value=sort_value, id=parsed_id)
