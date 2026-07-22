"""GET /metrics — see docs/observability.md#dashboards-and-metrics and
app/api/routes/metrics.py."""

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_metrics_requires_a_token(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 401


def test_metrics_rejects_an_incorrect_token(client: TestClient) -> None:
    response = client.get("/metrics", headers={"X-Metrics-Token": "wrong"})
    assert response.status_code == 401


def test_metrics_accepts_the_configured_token_via_header(client: TestClient) -> None:
    token = get_settings().metrics_token
    response = client.get("/metrics", headers={"X-Metrics-Token": token})
    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_metrics_accepts_the_configured_token_via_query_param(client: TestClient) -> None:
    token = get_settings().metrics_token
    response = client.get(f"/metrics?token={token}")
    assert response.status_code == 200


def test_metrics_reflects_a_request_that_was_just_made(client: TestClient) -> None:
    token = get_settings().metrics_token
    client.get("/health/live")
    response = client.get("/metrics", headers={"X-Metrics-Token": token})
    assert 'route="/health/live"' in response.text
