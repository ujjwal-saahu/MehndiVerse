import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

import 'artist_directory_models.dart';
import 'artist_models.dart';
import 'artist_scheduling_models.dart';

class ArtistException implements Exception {
  ArtistException(this.message);
  final String message;
}

/// Talks only to MehndiVerse's own backend (`/api/v1/artist/*`) — see
/// docs/artist-verification.md. Document/image bytes are uploaded here and
/// re-validated server-side; this repository never talks to Supabase Storage
/// directly (same boundary as ProfileRepository.uploadAvatar).
class ArtistRepository {
  ArtistRepository(this._dio);

  final Dio _dio;

  /// Lazily creates a draft application and promotes the caller's role to
  /// `artist` on first call — see app/api/routes/artist_onboarding.py's
  /// `get_my_artist_profile`. Call this to both "start onboarding" and to
  /// refresh the current verification status.
  Future<ArtistProfileData> fetchProfile() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/artist/profile');
      return ArtistProfileData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<ArtistProfileData> updateProfile(Map<String, dynamic> patch) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/v1/artist/profile',
        data: patch,
      );
      return ArtistProfileData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<ArtistProfileData> submitProfile() async {
    try {
      final response = await _dio.post<Map<String, dynamic>>('/api/v1/artist/profile/submit');
      return ArtistProfileData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<String> uploadProfileImage({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async {
    return _uploadImage(
      '/api/v1/artist/profile/image',
      bytes: bytes,
      filename: filename,
      contentType: contentType,
    );
  }

  Future<String> uploadCoverImage({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async {
    return _uploadImage(
      '/api/v1/artist/profile/cover-image',
      bytes: bytes,
      filename: filename,
      contentType: contentType,
    );
  }

  Future<String> _uploadImage(
    String path, {
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          bytes,
          filename: filename,
          contentType: MediaType.parse(contentType),
        ),
      });
      final response = await _dio.post<Map<String, dynamic>>(path, data: formData);
      return response.data!['image_url'] as String;
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<List<ArtistDocumentData>> fetchDocuments() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/artist/documents');
      return response.data!
          .map((entry) => ArtistDocumentData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<ArtistDocumentData> uploadDocument({
    required List<int> bytes,
    required String filename,
    required String contentType,
    required String documentType,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          bytes,
          filename: filename,
          contentType: MediaType.parse(contentType),
        ),
        'document_type': documentType,
      });
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/artist/documents',
        data: formData,
      );
      return ArtistDocumentData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  /// Customer-facing artist directory — see
  /// docs/artist-directory.md#directory-visibility.
  Future<ArtistDirectoryPageData> fetchDirectory({
    String? city,
    String? country,
    String? service,
    double? minRating,
    bool verifiedOnly = true,
    String? cursor,
    int limit = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/artists',
        queryParameters: {
          'city': ?city,
          'country': ?country,
          'service': ?service,
          'min_rating': ?minRating,
          'verified_only': verifiedOnly,
          'cursor': ?cursor,
          'limit': limit,
        },
      );
      return ArtistDirectoryPageData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<ArtistPublicProfileData> fetchPublicProfile(String artistId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/artists/$artistId');
      return ArtistPublicProfileData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<void> followArtist(String artistId) async {
    try {
      await _dio.post<void>('/api/v1/artists/$artistId/follow');
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  Future<void> unfollowArtist(String artistId) async {
    try {
      await _dio.delete<void>('/api/v1/artists/$artistId/follow');
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  /// Read-only slot calculation — see docs/artist-scheduling.md. Does not
  /// create a booking; booking creation is a later phase.
  Future<AvailableSlotsData> fetchAvailableSlots({
    required String artistId,
    required String serviceId,
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/artists/$artistId/availability/slots',
        queryParameters: {
          'service_id': serviceId,
          'start_date': _isoDate(startDate),
          'end_date': _isoDate(endDate),
        },
      );
      return AvailableSlotsData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ArtistException(_extractMessage(e));
    }
  }

  String _isoDate(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  String _extractMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return data['error']['message'] as String;
    }
    return e.message ?? 'Something went wrong. Please try again.';
  }
}
