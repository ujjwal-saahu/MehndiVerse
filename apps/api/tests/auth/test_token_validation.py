import uuid
from datetime import timedelta

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import InvalidTokenError, decode_access_token
from tests.auth.conftest import auth_headers, sign_token


def test_valid_token_decodes_to_expected_subject() -> None:
    user_id = uuid.uuid4()
    token = sign_token(user_id, email="valid@example.com")

    payload = decode_access_token(token)

    assert payload.user_id == user_id
    assert payload.email == "valid@example.com"


def test_expired_token_is_rejected() -> None:
    token = sign_token(uuid.uuid4(), expires_in=timedelta(seconds=-10))

    with pytest.raises(InvalidTokenError, match="expired"):
        decode_access_token(token)


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-jwt-at-all")


def test_token_signed_with_wrong_secret_is_rejected() -> None:
    token = sign_token(uuid.uuid4(), secret="a-completely-different-secret")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_missing_subject_is_rejected() -> None:
    claims = {"aud": "authenticated", "exp": 9999999999}
    token = pyjwt.encode(claims, get_settings().supabase_jwt_secret, algorithm="HS256")

    with pytest.raises(InvalidTokenError, match="subject"):
        decode_access_token(token)


def test_expired_token_rejected_by_protected_endpoint(client: TestClient) -> None:
    token = sign_token(uuid.uuid4(), expires_in=timedelta(seconds=-10))

    response = client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 401


def test_invalid_token_rejected_by_protected_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer complete-nonsense"})

    assert response.status_code == 401
