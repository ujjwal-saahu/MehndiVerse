import 'package:dio/dio.dart';

import '../gallery/gallery_repository.dart' show GalleryException;
import 'collection_models.dart';

/// Collections CRUD + items + reorder — see
/// docs/engagement-and-collections.md. Reuses [GalleryException] rather
/// than a parallel type, same call made throughout this app's other
/// backend-only repositories.
class CollectionRepository {
  CollectionRepository(this._dio);

  final Dio _dio;

  Future<CollectionListData> fetchMyCollections({String? cursor, int limit = 20}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/collections',
        queryParameters: {'limit': limit, 'cursor': ?cursor},
      );
      return CollectionListData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<CollectionData> createCollection({
    required String name,
    String? description,
    bool isPrivate = true,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/collections',
        data: {'name': name, 'description': ?description, 'is_private': isPrivate},
      );
      return CollectionData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<CollectionData> fetchCollection(String collectionId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/collections/$collectionId');
      return CollectionData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<CollectionData> updateCollection(
    String collectionId, {
    String? name,
    String? description,
    bool? isPrivate,
    String? coverDesignId,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/v1/collections/$collectionId',
        data: {
          'name': ?name,
          'description': ?description,
          'is_private': ?isPrivate,
          'cover_design_id': ?coverDesignId,
        },
      );
      return CollectionData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<void> deleteCollection(String collectionId) async {
    try {
      await _dio.delete<void>('/api/v1/collections/$collectionId');
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<CollectionItemsData> fetchItems(
    String collectionId, {
    String? cursor,
    int limit = 100,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/collections/$collectionId/items',
        queryParameters: {'limit': limit, 'cursor': ?cursor},
      );
      return CollectionItemsData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<CollectionItemsData> addItem(String collectionId, String designId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/collections/$collectionId/items',
        data: {'design_id': designId},
      );
      return CollectionItemsData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<void> removeItem(String collectionId, String designId) async {
    try {
      await _dio.delete<void>('/api/v1/collections/$collectionId/items/$designId');
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  Future<CollectionItemsData> reorderItems(String collectionId, List<String> designIds) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/api/v1/collections/$collectionId/items/reorder',
        data: {'design_ids': designIds},
      );
      return CollectionItemsData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCollectionException(e);
    }
  }

  GalleryException _toCollectionException(DioException e) {
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
