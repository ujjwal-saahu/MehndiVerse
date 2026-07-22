import 'package:dio/dio.dart';

import '../gallery/gallery_models.dart';
import '../gallery/gallery_repository.dart' show GalleryException;
import 'search_models.dart';

/// Talks only to MehndiVerse's own backend (`/api/v1/designs/search*`) — see
/// docs/design-search.md. Reuses [GalleryException] rather than defining a
/// parallel exception type: it's the same "backend-only call failed" shape
/// already used across the gallery feature.
class SearchRepository {
  SearchRepository(this._dio);

  final Dio _dio;

  Future<DesignListData> search({
    String? query,
    List<String> categoryIds = const [],
    String? artistId,
    bool? isPremium,
    String sort = 'relevance',
    String? cursor,
    int limit = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/designs/search',
        queryParameters: {
          'sort': sort,
          'limit': limit,
          'q': ?query,
          if (categoryIds.isNotEmpty) 'category_id': categoryIds,
          'artist_id': ?artistId,
          'is_premium': ?isPremium,
          'cursor': ?cursor,
        },
      );
      return DesignListData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toSearchException(e);
    }
  }

  Future<List<SearchSuggestionData>> suggest(String query) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/api/v1/designs/search/suggestions',
        queryParameters: {'q': query},
      );
      return response.data!
          .map((entry) => SearchSuggestionData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toSearchException(e);
    }
  }

  Future<List<SearchHistoryItemData>> fetchHistory() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/designs/search/history');
      return response.data!
          .map((entry) => SearchHistoryItemData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toSearchException(e);
    }
  }

  Future<void> clearHistory() async {
    try {
      await _dio.delete<void>('/api/v1/designs/search/history');
    } on DioException catch (e) {
      throw _toSearchException(e);
    }
  }

  GalleryException _toSearchException(DioException e) {
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
