"""AI feature flags — see docs/ai-foundation.md#feature-flags.

Recommendation-event collection moved to Phase 22's general analytics
system (`app/services/analytics/events.py`) — see tests/analytics/ for
those tests. This file now only covers the AI-specific feature-flag
mechanism (`app/services/ai/flags.py`), which is unrelated to and
unaffected by that change.
"""

from sqlalchemy.orm import Session

from app.db.models.system import SystemSetting
from app.services.ai.flags import is_ai_enabled, is_feature_enabled


def test_ai_features_default_enabled_with_no_settings_row(db_session: Session) -> None:
    assert is_ai_enabled(db_session) is True
    assert is_feature_enabled(db_session, "tag_suggestions") is True


def test_master_flag_off_disables_every_feature(db_session: Session) -> None:
    db_session.add(SystemSetting(key="ai.enabled", value={"enabled": False}))
    db_session.commit()

    assert is_ai_enabled(db_session) is False
    assert is_feature_enabled(db_session, "tag_suggestions") is False
    assert is_feature_enabled(db_session, "embeddings") is False


def test_per_feature_flag_off_only_disables_that_feature(db_session: Session) -> None:
    db_session.add(SystemSetting(key="ai.moderation.enabled", value={"enabled": False}))
    db_session.commit()

    assert is_feature_enabled(db_session, "moderation") is False
    assert is_feature_enabled(db_session, "tag_suggestions") is True
