"""app/core/alerts.py — see docs/observability.md#alerting."""

import httpx
import pytest
import respx

import app.core.alerts as alerts_module
from app.core.alerts import _last_sent_at, send_alert
from app.core.config import get_settings


class _FakeSettings:
    def __init__(self, webhook_url: str) -> None:
        self.alert_webhook_url = webhook_url


def test_send_alert_never_raises_with_no_webhook_configured() -> None:
    assert get_settings().alert_webhook_url == ""
    send_alert("test_event_no_webhook", detail="x")


def test_posts_to_webhook_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        alerts_module, "get_settings", lambda: _FakeSettings("https://hooks.example/test")
    )
    _last_sent_at.pop("test_event_webhook", None)

    with respx.mock:
        route = respx.post("https://hooks.example/test").mock(return_value=httpx.Response(200))
        send_alert("test_event_webhook", detail="x")
        assert route.called


def test_webhook_cooldown_prevents_a_second_post_within_the_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        alerts_module, "get_settings", lambda: _FakeSettings("https://hooks.example/test2")
    )
    _last_sent_at.pop("test_event_cooldown", None)

    with respx.mock:
        route = respx.post("https://hooks.example/test2").mock(return_value=httpx.Response(200))
        send_alert("test_event_cooldown", detail="first")
        send_alert("test_event_cooldown", detail="second")
        assert route.call_count == 1


def test_a_broken_webhook_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        alerts_module, "get_settings", lambda: _FakeSettings("https://hooks.example/broken")
    )
    _last_sent_at.pop("test_event_broken", None)

    with respx.mock:
        respx.post("https://hooks.example/broken").mock(side_effect=httpx.ConnectError("down"))
        send_alert("test_event_broken", detail="x")  # must not raise
