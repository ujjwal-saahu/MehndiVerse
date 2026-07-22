import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists auth tokens in the platform's secure storage (Keychain on iOS,
/// EncryptedSharedPreferences/Keystore-backed on Android) — never in plain
/// SharedPreferences. See docs/authentication.md#7.
class TokenStorage {
  TokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _accessTokenKey = 'mehndiverse.access_token';
  static const _refreshTokenKey = 'mehndiverse.refresh_token';

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  Future<String?> readRefreshToken() => _storage.read(key: _refreshTokenKey);

  Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }
}
