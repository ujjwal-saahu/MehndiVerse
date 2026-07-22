"""Tests for `register_exception_handlers`' localization behavior — see
app/core/exceptions.py and docs/localization-and-accessibility.md
#backend-message-localization. Uses a standalone throwaway FastAPI app (no
database needed) so these stay fast and independent of the real route
tree."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    register_exception_handlers,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/authentication-required")
    def _authentication_required() -> None:
        raise AuthenticationError()

    @app.get("/authentication-custom")
    def _authentication_custom() -> None:
        raise AuthenticationError("Token expired, please log in again.")

    @app.get("/authorization-required")
    def _authorization_required() -> None:
        raise AuthorizationError()

    @app.get("/app-error-custom")
    def _app_error_custom() -> None:
        raise AppError("This design has already been reviewed.")

    @app.get("/validated")
    def _validated(count: int) -> dict[str, int]:
        return {"count": count}

    @app.get("/boom")
    def _boom() -> None:
        raise ValueError("kaboom")

    return app


client = TestClient(_make_app(), raise_server_exceptions=False)


class TestAppErrorLocalization:
    def test_default_authentication_message_is_english_with_no_header(self) -> None:
        response = client.get("/authentication-required")
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Authentication required."

    def test_default_authentication_message_localizes_to_hindi(self) -> None:
        response = client.get("/authentication-required", headers={"Accept-Language": "hi-IN"})
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "प्रमाणीकरण आवश्यक है।"

    def test_default_authorization_message_localizes_to_arabic(self) -> None:
        response = client.get("/authorization-required", headers={"Accept-Language": "ar"})
        assert response.status_code == 403
        assert response.json()["error"]["message"] == "ليس لديك إذن للقيام بهذا الإجراء."

    def test_a_custom_authentication_message_is_never_translated(self) -> None:
        response = client.get("/authentication-custom", headers={"Accept-Language": "ur"})
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Token expired, please log in again."

    def test_a_custom_app_error_message_is_never_translated(self) -> None:
        response = client.get("/app-error-custom", headers={"Accept-Language": "hi"})
        assert response.status_code == 400
        assert response.json()["error"]["message"] == "This design has already been reviewed."


class TestValidationErrorLocalization:
    def test_defaults_to_english(self) -> None:
        response = client.get("/validated")
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "Request validation failed."

    def test_localizes_to_urdu(self) -> None:
        response = client.get("/validated", headers={"Accept-Language": "ur"})
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "درخواست کی توثیق ناکام ہو گئی۔"


class TestUnhandledExceptionLocalization:
    def test_localizes_to_arabic(self) -> None:
        response = client.get("/boom", headers={"Accept-Language": "ar"})
        assert response.status_code == 500
        assert response.json()["error"]["message"] == "حدث خطأ غير متوقع."
