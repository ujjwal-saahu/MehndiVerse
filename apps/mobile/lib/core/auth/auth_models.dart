import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_models.freezed.dart';

@freezed
class AuthUser with _$AuthUser {
  const factory AuthUser({
    required String id,
    required String email,
    required String role,
    required String status,
  }) = _AuthUser;
}

/// Auth state machine for the whole app. `role` on [AuthUser] always comes
/// from the backend's `/auth/me` response — never something the client
/// invents. See docs/authentication.md.
@freezed
class AuthState with _$AuthState {
  const factory AuthState.unauthenticated() = AuthStateUnauthenticated;
  const factory AuthState.authenticating() = AuthStateAuthenticating;
  const factory AuthState.authenticated(AuthUser user) = AuthStateAuthenticated;
  const factory AuthState.needsEmailVerification(String email) =
      AuthStateNeedsEmailVerification;
  const factory AuthState.error(String message) = AuthStateError;
}
