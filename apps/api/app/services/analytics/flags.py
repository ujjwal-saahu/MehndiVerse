"""Analytics feature flag — see docs/analytics-and-recommendations.md
#allow-analytics-to-be-disabled.

Reuses `SystemSetting` (the same mechanism `app/services/ai/flags.py`
already uses for AI feature flags) rather than a new flags table — one
operator-editable switch that, when off, stops every `record_event` call
from writing anything at all. This is the *operator*-level "disable
analytics" control; the *user*-level one is `UserPreference.analytics_
consent` (see `events.py`) — the two are independent and both must allow
an event through for it to be recorded with an identity attached.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.system import SystemSetting

ANALYTICS_ENABLED_KEY = "analytics.enabled"


def is_analytics_enabled(db: Session) -> bool:
    """Defaults to enabled when no `SystemSetting` row exists yet — a fresh
    environment collects analytics until an operator deliberately turns it
    off, the same default `app/services/ai/flags.py::is_ai_enabled` uses."""
    setting = db.execute(
        select(SystemSetting).where(SystemSetting.key == ANALYTICS_ENABLED_KEY)
    ).scalar_one_or_none()
    if setting is None:
        return True
    value = setting.value
    if isinstance(value, dict) and "enabled" in value:
        return bool(value["enabled"])
    return True
