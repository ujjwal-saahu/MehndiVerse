import 'package:dio/dio.dart';

import '../gallery/gallery_models.dart';
import '../gallery/gallery_repository.dart' show GalleryException;
import 'engagement_models.dart';

/// Likes and quick-saves — see docs/engagement-and-collections.md. Reuses
/// [GalleryException] rather than a parallel type, same call made for
/// Phase 8's `SearchRepository`.
class EngagementRepository {
  EngagementRepository(this._dio);

  final Dio _dio;

  Future<LikeStatusData> like(String designId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>('/api/v1/designs/$designId/like');
      return LikeStatusData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toEngagementException(e);
    }
  }

  Future<LikeStatusData> unlike(String designId) async {
    try {
      final response = await _dio.delete<Map<String, dynamic>>('/api/v1/designs/$designId/like');
      return LikeStatusData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toEngagementException(e);
    }
  }

  Future<SaveStatusData> save(String designId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>('/api/v1/designs/$designId/save');
      return SaveStatusData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toEngagementException(e);
    }
  }

  Future<SaveStatusData> unsave(String designId) async {
    try {
      final response = await _dio.delete<Map<String, dynamic>>('/api/v1/designs/$designId/save');
      return SaveStatusData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toEngagementException(e);
    }
  }

  Future<DesignListData> fetchSavedDesigns({String? cursor, int limit = 20}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/designs/saved',
        queryParameters: {'limit': limit, 'cursor': ?cursor},
      );
      return DesignListData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toEngagementException(e);
    }
  }

  GalleryException _toEngagementException(DioException e) {
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
