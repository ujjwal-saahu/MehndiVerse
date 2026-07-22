import 'package:dio/dio.dart';

import 'gallery_models.dart';

class GalleryException implements Exception {
  GalleryException(this.message, {this.isOffline = false});
  final String message;

  /// True when the failure looks like a connectivity problem (no response
  /// reached the server at all) rather than a server-side error — lets the
  /// UI show an offline-specific message. See
  /// docs/design-gallery.md#offline-friendly-error-state.
  final bool isOffline;
}

/// Talks only to MehndiVerse's own backend (`/api/v1/designs/*`,
/// `/api/v1/categories`) — see docs/authentication.md#2.
class GalleryRepository {
  GalleryRepository(this._dio);

  final Dio _dio;

  Future<List<CategoryData>> fetchCategories({String? categoryType}) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/api/v1/categories',
        queryParameters: {'category_type': ?categoryType},
      );
      return response.data!
          .map((entry) => CategoryData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toGalleryException(e);
    }
  }

  Future<HomeFeedData> fetchHomeFeed() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/designs/home-feed');
      return HomeFeedData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toGalleryException(e);
    }
  }

  Future<DesignListData> fetchPublishedDesigns({
    String? categoryId,
    String? difficultyLevel,
    String? bodyPlacement,
    String sort = 'latest',
    String? cursor,
    int limit = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/designs/published',
        queryParameters: {
          'sort': sort,
          'limit': limit,
          'category_id': ?categoryId,
          'difficulty_level': ?difficultyLevel,
          'body_placement': ?bodyPlacement,
          'cursor': ?cursor,
        },
      );
      return DesignListData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toGalleryException(e);
    }
  }

  Future<DesignDetailData> fetchDesign(String designId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/designs/$designId');
      return DesignDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toGalleryException(e);
    }
  }

  /// Enforced on the backend (premium access + monthly quota) — see
  /// docs/subscriptions-and-entitlements.md#download-limits. Returns the
  /// full-resolution image URL; a 403 (locked or quota exhausted) surfaces
  /// through [GalleryException].
  Future<String> downloadDesign(String designId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>('/api/v1/designs/$designId/download');
      return response.data!['image_url'] as String;
    } on DioException catch (e) {
      throw _toGalleryException(e);
    }
  }

  Future<List<DesignSummaryData>> fetchRelatedDesigns(String designId) async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/designs/$designId/related');
      return response.data!
          .map((entry) => DesignSummaryData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toGalleryException(e);
    }
  }

  /// Fire-and-forget from the caller's perspective — a failed view-count
  /// ping shouldn't disrupt viewing the design, so this deliberately doesn't
  /// throw a UI-facing exception; callers can ignore the returned future.
  Future<void> recordView(String designId) async {
    try {
      await _dio.post<void>('/api/v1/designs/$designId/view');
    } on DioException {
      // Best-effort only — see docs/design-gallery.md#view-count-event-handling.
    }
  }

  GalleryException _toGalleryException(DioException e) {
    final isOffline =
        e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout;
    if (isOffline) {
      return GalleryException(
        'You appear to be offline. Check your connection and try again.',
        isOffline: true,
      );
    }

    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return GalleryException(data['error']['message'] as String);
    }
    return GalleryException(e.message ?? 'Something went wrong. Please try again.');
  }
}
