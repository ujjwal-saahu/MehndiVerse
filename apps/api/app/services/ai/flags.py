"""AI feature flags — see docs/ai-foundation.md#feature-flags.

Reuses `SystemSetting` (Phase 2 schema, first given a read/write surface by
`app/api/routes/admin_settings.py` in Phase 17) rather than a new flags
table — a flag is exactly "a piece of runtime configuration staff can
change," which is precisely what that table already exists for. A flag
defaults to *enabled* when no `SystemSetting` row exists for it yet (so a
fresh environment behaves like AI is on until an operator deliberately
turns a capability off), and `ai.enabled` gates every other flag: turning
it off disables the whole module regardless of the per-capability flags.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.system import SystemSetting

AI_ENABLED_KEY = "ai.enabled"


def _flag_key(feature: str) -> str:
    return f"ai.{feature}.enabled"


def _read_flag(db: Session, key: str, *, default: bool) -> bool:
    setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    if setting is None:
        return default
    value = setting.value
    if isinstance(value, dict) and "enabled" in value:
        return bool(value["enabled"])
    return default


def is_ai_enabled(db: Session) -> bool:
    return _read_flag(db, AI_ENABLED_KEY, default=True)


def is_feature_enabled(db: Session, feature: str) -> bool:
    """`feature` is e.g. `"tag_suggestions"`, `"embeddings"`,
    `"duplicate_detection"`, `"moderation"`, `"generations"` — matches the
    job types this package enqueues under `docs/ai-foundation.md#feature-
    flags`'s naming."""
    if not is_ai_enabled(db):
        return False
    return _read_flag(db, _flag_key(feature), default=True)
