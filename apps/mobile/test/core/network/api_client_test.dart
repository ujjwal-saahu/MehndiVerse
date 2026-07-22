import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/auth/token_storage.dart';
import 'package:mobile/core/config/app_environment.dart';
import 'package:mobile/core/network/api_client.dart';

void main() {
  test('ApiClient configures Dio with the environment base URL', () {
    const env = AppEnvironment(apiBaseUrl: 'http://example.test', environmentName: 'test');
    final client = ApiClient(env, TokenStorage());

    expect(client.dio.options.baseUrl, 'http://example.test');
  });

  test('ApiClient attaches the auth interceptor', () {
    const env = AppEnvironment(apiBaseUrl: 'http://example.test', environmentName: 'test');
    final client = ApiClient(env, TokenStorage());

    expect(client.dio.interceptors, isNotEmpty);
  });
}
