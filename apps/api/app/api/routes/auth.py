import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthenticationError
from app.core.legal import CURRENT_PRIVACY_VERSION, CURRENT_TERMS_VERSION
from app.db.enums import AnalyticsEventType, ConsentType, UserRole, UserStatus
from app.db.models.user import Profile, User, UserPreference
from app.db.session import get_db_session
from app.integrations import supabase_auth
from app.integrations.supabase_auth import SupabaseAuthError
from app.schemas.auth import (
    AccountDeletionResponse,
    LoginRequest,
    PasswordResetRequest,
    ReauthRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserOut,
)
from app.services.analytics.events import record_event
from app.services.audit import record_audit_log
from app.services.legal import record_consent
from app.services.login_security import clear_failed_logins, is_locked_out, record_failed_login


def _verify_reauth(current: AuthenticatedUser, password: str) -> None:
    """Re-verifies the caller's current password against Supabase before a
    privileged, hard-to-reverse action — see docs/security-review.md
    #privileged-action-reauthentication. A valid bearer token alone isn't
    enough for these: it only proves *a* session is live, not that whoever
    is driving it right now is the account holder (e.g. a hijacked/left-open
    session, or a stolen-but-not-yet-expired token)."""
    try:
        supabase_auth.sign_in_with_password(current.user.email, password)
    except SupabaseAuthError as exc:
        raise AuthenticationError("Incorrect password.") from exc


router = APIRouter(prefix="/auth", tags=["auth"])


def _rate_limit() -> str:
    return get_settings().auth_rate_limit


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit(_rate_limit())
def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_db_session)
) -> RegisterResponse:
    if not payload.terms_accepted:
        raise AppError(
            "You must accept the Terms of Service and Privacy Policy to register.",
            status_code=422,
        )
    try:
        result = supabase_auth.sign_up(payload.email, payload.password)
    except SupabaseAuthError as exc:
        raise AppError(exc.message, status_code=min(exc.status_code, 422)) from exc

    user_id = uuid.UUID(result.user_id)
    existing = db.get(User, user_id)
    if existing is None:
        # Registration always creates a `customer` — no client input can set a
        # different role. See docs/authentication.md#3.
        user = User(id=user_id, email=result.email, role=UserRole.CUSTOMER.value)
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id, display_name=result.email.split("@")[0]))
        db.add(UserPreference(user_id=user.id))
        record_event(
            db,
            event_type=AnalyticsEventType.REGISTRATION_COMPLETED.value,
            user_id=user.id,
        )
        record_consent(
            db,
            user_id=user.id,
            consent_type=ConsentType.TERMS_OF_SERVICE.value,
            version=CURRENT_TERMS_VERSION,
            granted=True,
        )
        record_consent(
            db,
            user_id=user.id,
            consent_type=ConsentType.PRIVACY_POLICY.value,
            version=CURRENT_PRIVACY_VERSION,
            granted=True,
        )
        db.commit()

    if result.session is None:
        return RegisterResponse(
            message="Registration successful. Please check your email to verify your account.",
            session=None,
        )

    return RegisterResponse(
        message="Registration successful.",
        session=TokenResponse(
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
            expires_in=result.session.expires_in,
        ),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_rate_limit())
def login(
    request: Request, payload: LoginRequest, db: Session = Depends(get_db_session)
) -> TokenResponse:
    # Account-keyed lockout, on top of the IP-based rate limit above — see
    # app/services/login_security.py. Checked (and the generic message
    # reused) before calling Supabase so a locked-out attacker can't use
    # response-timing to distinguish "locked out" from "wrong password".
    if is_locked_out(payload.email):
        raise AuthenticationError("Invalid email or password.")

    try:
        session = supabase_auth.sign_in_with_password(payload.email, payload.password)
    except SupabaseAuthError as exc:
        attempts = record_failed_login(payload.email)
        settings = get_settings()
        if attempts == settings.login_lockout_threshold:
            record_audit_log(
                db,
                request=request,
                actor_id=None,
                action="login.lockout_triggered",
                entity_type="user",
                entity_id=None,
                after_state={"email": payload.email, "attempts": attempts},
            )
            db.commit()
        # Deliberately generic — never confirm whether the email is registered.
        raise AuthenticationError("Invalid email or password.") from exc

    clear_failed_logins(payload.email)

    user = db.get(User, uuid.UUID(session.user_id))
    if user is not None:
        user.last_login_at = datetime.now(UTC)
        db.add(user)
        db.commit()

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
    )


@router.post("/logout", status_code=204)
def logout(current: AuthenticatedUser = Depends(get_current_user)) -> None:
    try:
        supabase_auth.sign_out(current.access_token)
    except SupabaseAuthError:
        # Already invalid/expired upstream — logging out locally still succeeds.
        pass


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(_rate_limit())
def refresh(request: Request, payload: RefreshRequest) -> TokenResponse:
    try:
        session = supabase_auth.refresh_session(payload.refresh_token)
    except SupabaseAuthError as exc:
        raise AuthenticationError("Invalid or expired refresh token.") from exc

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
    )


@router.post("/password-reset/request", status_code=202)
@limiter.limit(_rate_limit())
def request_password_reset(request: Request, payload: PasswordResetRequest) -> dict[str, str]:
    try:
        supabase_auth.send_password_reset(payload.email)
    except SupabaseAuthError:
        pass  # never reveal whether the email is registered
    return {"message": "If an account exists for this email, a password reset link has been sent."}


@router.post("/verify-email/resend", status_code=202)
@limiter.limit(_rate_limit())
def resend_verification(request: Request, payload: ResendVerificationRequest) -> dict[str, str]:
    try:
        supabase_auth.resend_verification_email(payload.email)
    except SupabaseAuthError:
        pass
    return {"message": "If an account exists for this email, a verification email has been sent."}


@router.get("/me", response_model=UserOut)
def me(current: AuthenticatedUser = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current.user.id,
        email=current.user.email,
        role=current.effective_role,
        status=current.user.status,
        created_at=current.user.created_at,
    )


@router.post("/account/deletion-request", response_model=AccountDeletionResponse)
def request_account_deletion(
    request: Request,
    payload: ReauthRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AccountDeletionResponse:
    _verify_reauth(current, payload.password)

    user = current.user
    if user.deletion_requested_at is not None:
        raise AppError("Account deletion has already been requested.", status_code=409)

    user.deletion_requested_at = datetime.now(UTC)
    user.status = UserStatus.PENDING_DELETION.value
    db.add(user)
    record_audit_log(
        db,
        request=request,
        actor_id=user.id,
        action="account.deletion_requested",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)

    return AccountDeletionResponse(
        message="Account deletion requested. Your account will be deactivated.",
        deletion_requested_at=user.deletion_requested_at,
    )


@router.post("/sessions/revoke-all", status_code=204)
def revoke_all_sessions(
    request: Request,
    payload: ReauthRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    """Signs out every session for this account, including the one making
    this request — see docs/security-review.md#session-revocation. Intended
    for "sign out everywhere" after a suspected compromise; the client that
    called this will itself get a 401 on its next request and must log back
    in, same as any other revoked session."""
    _verify_reauth(current, payload.password)

    try:
        supabase_auth.sign_out(current.access_token, scope="global")
    except SupabaseAuthError as exc:
        raise AppError("Failed to revoke sessions. Please try again.", status_code=502) from exc

    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="session.revoke_all",
        entity_type="user",
        entity_id=current.user.id,
    )
    db.commit()
