from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_reports_status_shape() -> None:
    response = client.get("/health")
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"ok", "unavailable"}
    assert body["cache"] in {"ok", "unavailable"}


def test_liveness_returns_200_with_no_dependency_checks() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_unavailable_sends_a_database_health_alert(monkeypatch) -> None:
    """See docs/observability.md#database-health-alerts."""
    from sqlalchemy.exc import SQLAlchemyError

    import app.api.routes.health as health_module

    class _BrokenEngine:
        def connect(self):
            raise SQLAlchemyError("connection refused")

    sent: list[str] = []
    monkeypatch.setattr(health_module, "get_engine", lambda: _BrokenEngine())
    monkeypatch.setattr(health_module, "send_alert", lambda event, **details: sent.append(event))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "unavailable"
    assert sent == ["database_unavailable"]
