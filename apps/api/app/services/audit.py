"""Immutable audit-log writes — see docs/artist-verification.md#audit-log.

`AuditLog` (app/db/models/system.py) existed since Phase 2 but nothing wrote
to it until this phase. This module is the first (and, so callers don't each
reinvent the ip/user-agent extraction, hopefully only) place that does.
"""

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models.system import AuditLog


def record_audit_log(
    db: Session,
    *,
    request: Request,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
) -> None:
    """Adds the row to `db` but does not commit — callers write the audit
    entry in the same transaction as the change it describes, so the two can
    never disagree (a commit failure rolls back both together)."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
