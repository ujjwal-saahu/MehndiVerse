import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/config/app_environment.dart';

void main() {
  test('development() returns the local API base URL', () {
    final env = AppEnvironment.development();

    expect(env.apiBaseUrl, 'http://localhost:8000');
    expect(env.environmentName, 'development');
  });

  test('supports value equality', () {
    const a = AppEnvironment(apiBaseUrl: 'http://a', environmentName: 'test');
    const b = AppEnvironment(apiBaseUrl: 'http://a', environmentName: 'test');

    expect(a, equals(b));
  });
}
