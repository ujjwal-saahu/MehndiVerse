"""See docs/security-review.md#security-headers and
app/core/security_headers.py."""

from fastapi.testclient import TestClient


def test_response_includes_baseline_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_hsts_is_absent_outside_production(client: TestClient) -> None:
    response = client.get("/health")
    assert "strict-transport-security" not in {k.lower() for k in response.headers}
