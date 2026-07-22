import 'package:dio/dio.dart';

import 'booking_models.dart';

class BookingException implements Exception {
  BookingException(this.message);
  final String message;
}

/// Customer-facing booking actions — see docs/booking-lifecycle.md. Talks
/// only to MehndiVerse's own backend (`/api/v1/bookings/*`), same boundary
/// as ArtistRepository.
class BookingRepository {
  BookingRepository(this._dio);

  final Dio _dio;

  Future<List<BookingSummaryData>> fetchMyBookings() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/bookings/mine');
      return response.data!
          .map((entry) => BookingSummaryData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> fetchBooking(String bookingId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/bookings/$bookingId');
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> createDraft({required String artistProfileId}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings',
        data: {'artist_profile_id': artistProfileId},
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> updateDraft(String bookingId, Map<String, dynamic> patch) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId',
        data: patch,
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> submitBooking(String bookingId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/submit',
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> cancelBooking(String bookingId, {String? reason}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/cancel',
        data: {'reason': reason},
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> rescheduleBooking(
    String bookingId, {
    required String newDate,
    String? newTime,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/reschedule',
        data: {'new_date': newDate, 'new_time': newTime},
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> acceptQuote(String bookingId, String quoteId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/quotes/$quoteId/accept',
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
    }
  }

  Future<BookingDetailData> rejectQuote(String bookingId, String quoteId, {String? reason}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/bookings/$bookingId/quotes/$quoteId/reject',
        data: {'reason': reason},
      );
      return BookingDetailData.fromJson(response.data!);
    } on DioException catch (e) {
      throw BookingException(_extractMessage(e));
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
