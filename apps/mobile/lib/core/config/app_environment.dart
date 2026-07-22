import 'package:freezed_annotation/freezed_annotation.dart';

part 'app_environment.freezed.dart';

@freezed
class AppEnvironment with _$AppEnvironment {
  const factory AppEnvironment({
    required String apiBaseUrl,
    required String environmentName,
  }) = _AppEnvironment;

  factory AppEnvironment.development() => const AppEnvironment(
        apiBaseUrl: 'http://localhost:8000',
        environmentName: 'development',
      );
}
