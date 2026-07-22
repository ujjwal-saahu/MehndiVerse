import 'package:dio/dio.dart';

import 'auth_models.dart';

class AuthException implements Exception {
  AuthException(this.message);
  final String message;
}

class TokenPair {
  const TokenPair({required this.accessToken, required this.refreshToken});
  final String accessToken;
  final String refreshToken;
}

class RegisterResult {
  const RegisterResult({required this.message, this.session});
  final String message;
  final TokenPair? session;
}

/// Talks only to MehndiVerse's own backend (`/api/v1/auth/*`) — never
/// directly to Supabase. See docs/authentication.md#2.
class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;

  Future<RegisterResult> register({required String email, required String password}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/auth/register',
        data: {'email': email, 'password': password},
      );
      final data = response.data!;
      final sessionJson = data['session'] as Map<String, dynamic>?;
      return RegisterResult(
        message: data['message'] as String,
        session: sessionJson == null
            ? null
            : TokenPair(
                accessToken: sessionJson['access_token'] as String,
                refreshToken: sessionJson['refresh_token'] as String,
              ),
      );
    } on DioException catch (e) {
      throw AuthException(_extractMessage(e));
    }
  }

  Future<TokenPair> login({required String email, required String password}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/auth/login',
        data: {'email': email, 'password': password},
      );
      final data = response.data!;
      return TokenPair(
        accessToken: data['access_token'] as String,
        refreshToken: data['refresh_token'] as String,
      );
    } on DioException catch (e) {
      throw AuthException(_extractMessage(e));
    }
  }

  Future<void> logout() async {
    try {
      await _dio.post<void>('/api/v1/auth/logout');
    } on DioException {
      // Best-effort: local session is cleared regardless by the caller.
    }
  }

  Future<void> requestPasswordReset(String email) async {
    await _dio.post<void>('/api/v1/auth/password-reset/request', data: {'email': email});
  }

  Future<void> resendVerification(String email) async {
    await _dio.post<void>('/api/v1/auth/verify-email/resend', data: {'email': email});
  }

  Future<AuthUser> fetchCurrentUser() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/auth/me');
      final data = response.data!;
      return AuthUser(
        id: data['id'] as String,
        email: data['email'] as String,
        role: data['role'] as String,
        status: data['status'] as String,
      );
    } on DioException catch (e) {
      throw AuthException(_extractMessage(e));
    }
  }

  Future<void> requestAccountDeletion() async {
    try {
      await _dio.post<void>('/api/v1/auth/account/deletion-request');
    } on DioException catch (e) {
      throw AuthException(_extractMessage(e));
    }
  }

  String _extractMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return data['error']['message'] as String;
    }
    return e.message ?? 'Something went wrong. Please try again.';
  }
}
