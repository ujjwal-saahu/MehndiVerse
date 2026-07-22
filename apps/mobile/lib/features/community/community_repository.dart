import 'package:dio/dio.dart';

import 'community_models.dart';

class CommunityException implements Exception {
  CommunityException(this.message, {this.isOffline = false});
  final String message;
  final bool isOffline;
}

/// Comments, reviews, and reporting — see docs/community-and-trust.md.
/// Mirrors apps/web's `/api/designs/{id}/comments`,
/// `/api/comments/{id}`, `/api/bookings/{id}/reviews`,
/// `/api/artists/{id}/reviews`, and the design/comment/user report
/// endpoints, but talks to the FastAPI backend directly (no BFF proxy — see
/// app/features/gallery/gallery_repository.dart for why mobile skips that
/// layer that the web app needs for its httpOnly-cookie session).
class CommunityRepository {
  CommunityRepository(this._dio);

  final Dio _dio;

  Future<List<CommentData>> fetchComments(String designId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/designs/$designId/comments',
      );
      final items = response.data!['items'] as List<dynamic>;
      return items.map((entry) => CommentData.fromJson(entry as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<CommentData> createComment(
    String designId, {
    required String body,
    String? parentCommentId,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/designs/$designId/comments',
        data: {'body': body, 'parent_comment_id': parentCommentId},
      );
      return CommentData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<void> updateComment(String commentId, {required String body}) async {
    try {
      await _dio.patch<Map<String, dynamic>>(
        '/api/v1/comments/$commentId',
        data: {'body': body},
      );
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<void> deleteComment(String commentId) async {
    try {
      await _dio.delete<void>('/api/v1/comments/$commentId');
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<void> reportComment(String commentId, {required String reason}) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/api/v1/comments/$commentId/report',
        data: {'reason': reason},
      );
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<void> reportDesign(String designId, {required String reason}) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/api/v1/designs/$designId/report',
        data: {'reason': reason},
      );
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<void> reportUser(String userId, {required String reason}) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/api/v1/users/$userId/report',
        data: {'reason': reason},
      );
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<ReviewData> createReview(
    String bookingId, {
    required int rating,
    String? body,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/reviews',
        data: {'rating': rating, 'body': body},
      );
      return ReviewData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  Future<ReviewListData> fetchArtistReviews(String artistProfileId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/artists/$artistProfileId/reviews',
      );
      return ReviewListData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toCommunityException(e);
    }
  }

  CommunityException _toCommunityException(DioException e) {
    final isOffline =
        e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout;
    if (isOffline) {
      return CommunityException(
        'You appear to be offline. Check your connection and try again.',
        isOffline: true,
      );
    }

    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return CommunityException(data['error']['message'] as String);
    }
    return CommunityException(e.message ?? 'Something went wrong. Please try again.');
  }
}
