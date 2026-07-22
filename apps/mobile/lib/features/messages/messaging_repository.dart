import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

import 'messaging_models.dart';

class MessagingException implements Exception {
  MessagingException(this.message);
  final String message;
}

/// Booking-scoped messaging — see docs/booking-messaging.md. Customer- and
/// artist-facing: both roles use the same endpoints, from their own
/// perspective (the backend resolves "the other party" per caller).
class MessagingRepository {
  MessagingRepository(this._dio);

  final Dio _dio;

  Future<List<ConversationSummaryData>> fetchConversations() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/conversations');
      return response.data!
          .map((e) => ConversationSummaryData.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw MessagingException(_extractMessage(e));
    }
  }

  Future<MessagePageData> fetchMessages(String bookingId, {String? cursor}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/conversation/messages',
        queryParameters: {'cursor': ?cursor},
      );
      return MessagePageData.fromJson(response.data!);
    } on DioException catch (e) {
      throw MessagingException(_extractMessage(e));
    }
  }

  Future<MessageData> sendTextMessage(String bookingId, String body) async {
    try {
      final formData = FormData.fromMap({'body': body});
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/conversation/messages',
        data: formData,
      );
      return MessageData.fromJson(response.data!);
    } on DioException catch (e) {
      throw MessagingException(_extractMessage(e));
    }
  }

  Future<MessageData> sendImageMessage({
    required String bookingId,
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
        '/api/v1/bookings/$bookingId/conversation/messages',
        data: formData,
      );
      return MessageData.fromJson(response.data!);
    } on DioException catch (e) {
      throw MessagingException(_extractMessage(e));
    }
  }

  Future<void> markConversationRead(String bookingId) async {
    try {
      await _dio.post<void>('/api/v1/bookings/$bookingId/conversation/read');
    } on DioException catch (e) {
      throw MessagingException(_extractMessage(e));
    }
  }

  Future<void> reportMessage(String messageId, {required String reason}) async {
    try {
      await _dio.post<void>(
        '/api/v1/messages/$messageId/report',
        data: {'reason': reason},
      );
    } on DioException catch (e) {
      throw MessagingException(_extractMessage(e));
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
