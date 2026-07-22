import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_models.dart';
import 'auth_repository.dart';
import 'token_storage.dart';

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._repository, this._tokenStorage)
      : super(const AuthState.unauthenticated()) {
    _restoreSession();
  }

  final AuthRepository _repository;
  final TokenStorage _tokenStorage;

  Future<void> _restoreSession() async {
    final accessToken = await _tokenStorage.readAccessToken();
    if (accessToken == null) return;

    state = const AuthState.authenticating();
    try {
      final user = await _repository.fetchCurrentUser();
      state = AuthState.authenticated(user);
    } on AuthException {
      await _tokenStorage.clear();
      state = const AuthState.unauthenticated();
    }
  }

  Future<void> register({required String email, required String password}) async {
    state = const AuthState.authenticating();
    try {
      final result = await _repository.register(email: email, password: password);
      final session = result.session;
      if (session == null) {
        state = AuthState.needsEmailVerification(email);
        return;
      }
      await _tokenStorage.saveTokens(
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
      );
      final user = await _repository.fetchCurrentUser();
      state = AuthState.authenticated(user);
    } on AuthException catch (e) {
      state = AuthState.error(e.message);
    }
  }

  Future<void> login({required String email, required String password}) async {
    state = const AuthState.authenticating();
    try {
      final tokens = await _repository.login(email: email, password: password);
      await _tokenStorage.saveTokens(
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
      );
      final user = await _repository.fetchCurrentUser();
      state = AuthState.authenticated(user);
    } on AuthException catch (e) {
      state = AuthState.error(e.message);
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    await _tokenStorage.clear();
    state = const AuthState.unauthenticated();
  }

  Future<void> requestPasswordReset(String email) async {
    await _repository.requestPasswordReset(email);
  }

  Future<void> resendVerification(String email) async {
    await _repository.resendVerification(email);
  }

  Future<void> requestAccountDeletion() async {
    await _repository.requestAccountDeletion();
    await logout();
  }

  void clearError() {
    if (state is AuthStateError) {
      state = const AuthState.unauthenticated();
    }
  }
}
