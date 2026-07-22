from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.i18n import resolve_locale, translate
from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for application-raised errors that map to a known HTTP response."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        *,
        code: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        # Set only when `message` is still the class's own default (see the
        # subclasses below) — a caller-supplied message is never
        # translated, so overriding one still means exactly what it says.
        self.code = code
        super().__init__(message)


class AuthenticationError(AppError):
    """Missing, invalid, or expired credentials (401)."""

    _DEFAULT_MESSAGE = "Authentication required."

    def __init__(self, message: str = _DEFAULT_MESSAGE) -> None:
        code = "auth.required" if message == self._DEFAULT_MESSAGE else None
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, code=code)


class AuthorizationError(AppError):
    """Authenticated, but not permitted to perform this action (403)."""

    _DEFAULT_MESSAGE = "You do not have permission to perform this action."

    def __init__(self, message: str = _DEFAULT_MESSAGE) -> None:
        code = "auth.forbidden" if message == self._DEFAULT_MESSAGE else None
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, code=code)


def _error_body(code: str, message: str) -> dict[str, object]:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", path=request.url.path, message=exc.message)
        message = exc.message
        if exc.code is not None:
            locale = resolve_locale(request.headers.get("accept-language"))
            message = translate(exc.code, locale) or exc.message
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("app_error", message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("validation_error", path=request.url.path, errors=exc.errors())
        locale = resolve_locale(request.headers.get("accept-language"))
        message = translate("validation.failed", locale) or "Request validation failed."
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("validation_error", message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.info("http_exception", path=request.url.path, status_code=exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=request.url.path, exc_info=exc)
        locale = resolve_locale(request.headers.get("accept-language"))
        message = translate("error.internal", locale) or "An unexpected error occurred."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", message),
        )
