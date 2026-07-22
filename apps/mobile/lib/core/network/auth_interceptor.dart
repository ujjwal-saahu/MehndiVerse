import 'package:dio/dio.dart';

import '../auth/token_storage.dart';

/// Attaches the stored access token to every request and, on a single 401,
/// attempts one silent refresh (via a bare Dio instance, bypassing this
/// interceptor to avoid a retry loop) before giving up and clearing the
/// session.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.tokenStorage, required this.baseUrl});

  final TokenStorage tokenStorage;
  final String baseUrl;

  bool _isRefreshing = false;

  static const _authEndpointPaths = ['/auth/login', '/auth/register', '/auth/refresh'];

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await tokenStorage.readAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final isAuthEndpoint = _authEndpointPaths.any(err.requestOptions.path.contains);

    if (err.response?.statusCode != 401 || isAuthEndpoint || _isRefreshing) {
      handler.next(err);
      return;
    }

    final refreshToken = await tokenStorage.readRefreshToken();
    if (refreshToken == null) {
      handler.next(err);
      return;
    }

    _isRefreshing = true;
    try {
      final refreshDio = Dio(BaseOptions(baseUrl: baseUrl));
      final response = await refreshDio.post<Map<String, dynamic>>(
        '/api/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final data = response.data!;
      final newAccessToken = data['access_token'] as String;
      final newRefreshToken = data['refresh_token'] as String;
      await tokenStorage.saveTokens(accessToken: newAccessToken, refreshToken: newRefreshToken);

      final retryDio = Dio(BaseOptions(baseUrl: baseUrl));
      final retryOptions = err.requestOptions;
      retryOptions.headers['Authorization'] = 'Bearer $newAccessToken';
      final retryResponse = await retryDio.fetch<dynamic>(retryOptions);
      handler.resolve(retryResponse);
    } on DioException {
      await tokenStorage.clear();
      handler.next(err);
    } finally {
      _isRefreshing = false;
    }
  }
}
