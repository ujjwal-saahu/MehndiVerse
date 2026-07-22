import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/auth/auth_controller.dart';
import 'package:mobile/core/auth/auth_models.dart';
import 'package:mobile/core/auth/auth_repository.dart';

import '../../test_utils/fake_auth.dart';

class _StubAuthRepository implements AuthRepository {
  _StubAuthRepository({
    this.registerResult,
    this.loginTokens,
    this.loginError,
    this.currentUser,
  });

  RegisterResult? registerResult;
  TokenPair? loginTokens;
  AuthException? loginError;
  AuthUser? currentUser;
  bool loggedOut = false;
  bool deletionRequested = false;

  @override
  Future<RegisterResult> register({required String email, required String password}) async {
    return registerResult!;
  }

  @override
  Future<TokenPair> login({required String email, required String password}) async {
    if (loginError != null) throw loginError!;
    return loginTokens!;
  }

  @override
  Future<void> logout() async {
    loggedOut = true;
  }

  @override
  Future<void> requestPasswordReset(String email) async {}

  @override
  Future<void> resendVerification(String email) async {}

  @override
  Future<AuthUser> fetchCurrentUser() async => currentUser!;

  @override
  Future<void> requestAccountDeletion() async {
    deletionRequested = true;
  }
}

void main() {
  test('login transitions to authenticated on success', () async {
    const user = AuthUser(id: 'u1', email: 'a@b.com', role: 'customer', status: 'active');
    final repository = _StubAuthRepository(
      loginTokens: const TokenPair(accessToken: 'at', refreshToken: 'rt'),
      currentUser: user,
    );
    final controller = AuthController(repository, NoopTokenStorage());

    await controller.login(email: 'a@b.com', password: 'password123');

    expect(controller.state, const AuthState.authenticated(user));
  });

  test('login transitions to error on failure', () async {
    final repository = _StubAuthRepository(loginError: AuthException('Invalid email or password.'));
    final controller = AuthController(repository, NoopTokenStorage());

    await controller.login(email: 'a@b.com', password: 'wrong');

    expect(controller.state, const AuthState.error('Invalid email or password.'));
  });

  test('register without a session transitions to needsEmailVerification', () async {
    final repository = _StubAuthRepository(
      registerResult: const RegisterResult(message: 'check your email'),
    );
    final controller = AuthController(repository, NoopTokenStorage());

    await controller.register(email: 'new@example.com', password: 'password123');

    expect(
      controller.state,
      const AuthState.needsEmailVerification('new@example.com'),
    );
  });

  test('logout clears state back to unauthenticated', () async {
    const user = AuthUser(id: 'u1', email: 'a@b.com', role: 'customer', status: 'active');
    final repository = _StubAuthRepository(currentUser: user);
    final controller = AuthController(repository, NoopTokenStorage());
    controller.state = const AuthState.authenticated(user);

    await controller.logout();

    expect(controller.state, const AuthState.unauthenticated());
    expect(repository.loggedOut, isTrue);
  });
}
