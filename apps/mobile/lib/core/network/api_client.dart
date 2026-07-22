import 'package:dio/dio.dart';

import '../auth/token_storage.dart';
import '../config/app_environment.dart';
import 'auth_interceptor.dart';

class ApiClient {
  ApiClient(AppEnvironment environment, TokenStorage tokenStorage)
      : dio = Dio(
          BaseOptions(
            baseUrl: environment.apiBaseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 10),
          ),
        ) {
    dio.interceptors.add(
      AuthInterceptor(tokenStorage: tokenStorage, baseUrl: environment.apiBaseUrl),
    );
  }

  final Dio dio;
}
