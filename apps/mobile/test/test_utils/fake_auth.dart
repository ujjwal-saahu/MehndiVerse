import 'package:dio/dio.dart';
import 'package:mobile/core/auth/auth_controller.dart';
import 'package:mobile/core/auth/auth_models.dart';
import 'package:mobile/core/auth/auth_repository.dart';
import 'package:mobile/core/auth/token_storage.dart';

/// In-memory TokenStorage that never touches the flutter_secure_storage
/// platform channel — safe to use in plain `flutter test` (no platform
/// bindings available there).
class NoopTokenStorage implements TokenStorage {
  @override
  Future<String?> readAccessToken() async => null;

  @override
  Future<String?> readRefreshToken() async => null;

  @override
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {}

  @override
  Future<void> clear() async {}
}

/// An [AuthController] pinned to a fixed state for widget tests, so screens
/// can be exercised without a real backend or platform plugins.
class FakeAuthController extends AuthController {
  FakeAuthController(AuthState initialState)
      : super(
          AuthRepository(
            Dio(
              BaseOptions(
                baseUrl: 'http://localhost:1',
                connectTimeout: const Duration(milliseconds: 50),
              ),
            ),
          ),
          NoopTokenStorage(),
        ) {
    state = initialState;
  }
}
