import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

import 'profile_models.dart';

class ProfileException implements Exception {
  ProfileException(this.message);
  final String message;
}

/// Talks only to MehndiVerse's own backend (`/api/v1/users/*`) — see
/// docs/profile-and-privacy.md. Avatar bytes are uploaded here and re-encoded
/// server-side; this repository never talks to Supabase Storage directly.
class ProfileRepository {
  ProfileRepository(this._dio);

  final Dio _dio;

  Future<ProfileData> fetchProfile() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/users/me/profile');
      return ProfileData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<ProfileData> updateProfile({
    String? displayName,
    String? bio,
    String? city,
    String? country,
    String? locale,
    String? timezone,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/v1/users/me/profile',
        data: {
          'display_name': ?displayName,
          'bio': ?bio,
          'city': ?city,
          'country': ?country,
          'locale': ?locale,
          'timezone': ?timezone,
        },
      );
      return ProfileData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<String> uploadAvatar({
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
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/users/me/avatar',
        data: formData,
      );
      return response.data!['avatar_url'] as String;
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<PreferencesData> fetchPreferences() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/users/me/preferences');
      return PreferencesData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<PreferencesData> updatePreferences({
    bool? emailNotifications,
    bool? pushNotifications,
    bool? smsNotifications,
    bool? marketingOptIn,
    String? profileVisibility,
    bool? showLocation,
    bool? allowMessagesFromStrangers,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/v1/users/me/preferences',
        data: {
          'email_notifications': ?emailNotifications,
          'push_notifications': ?pushNotifications,
          'sms_notifications': ?smsNotifications,
          'marketing_opt_in': ?marketingOptIn,
          'profile_visibility': ?profileVisibility,
          'show_location': ?showLocation,
          'allow_messages_from_strangers': ?allowMessagesFromStrangers,
        },
      );
      return PreferencesData.fromJson(response.data!);
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<List<BlockedUser>> fetchBlockedUsers() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/users/me/blocks');
      return response.data!
          .map((entry) => BlockedUser.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<void> blockUser(String userId) async {
    try {
      await _dio.post<void>('/api/v1/users/me/blocks', data: {'user_id': userId});
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  Future<void> unblockUser(String userId) async {
    try {
      await _dio.delete<void>('/api/v1/users/me/blocks/$userId');
    } on DioException catch (e) {
      throw ProfileException(_extractMessage(e));
    }
  }

  String _extractMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return data['error']['message'] as String;
    }
    return e.message ?? 'Something went wrong. Please try again.';
  }
}
