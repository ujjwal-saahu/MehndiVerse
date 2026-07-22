"""app/core/request_context.py — see docs/observability.md#correlation-
ids-and-request-ids."""

import uuid

from fastapi.testclient import TestClient


def test_response_includes_a_generated_request_id(client: TestClient) -> None:
    response = client.get("/health/live")
    request_id = response.headers.get("x-request-id")
    assert request_id
    uuid.UUID(request_id)  # raises if not a valid UUID


def test_correlation_id_defaults_to_the_request_id_when_not_supplied(
    client: TestClient,
) -> None:
    response = client.get("/health/live")
    assert response.headers["x-correlation-id"] == response.headers["x-request-id"]


def test_client_supplied_request_id_is_echoed_back(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "my-request-id"})
    assert response.headers["x-request-id"] == "my-request-id"


def test_client_supplied_correlation_id_is_preserved_independently(
    client: TestClient,
) -> None:
    response = client.get(
        "/health/live",
        headers={"X-Request-ID": "my-request-id", "X-Correlation-ID": "my-correlation-id"},
    )
    assert response.headers["x-request-id"] == "my-request-id"
    assert response.headers["x-correlation-id"] == "my-correlation-id"
