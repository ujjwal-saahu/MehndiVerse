import 'package:dio/dio.dart';

import 'subscription_models.dart';

class SubscriptionException implements Exception {
  SubscriptionException(this.message);
  final String message;
}

/// Subscription plan browsing and self-service management — see
/// docs/subscriptions-and-entitlements.md. Deliberately no checkout method
/// here: no payment SDK exists anywhere in this app (bookings don't
/// integrate Razorpay in Flutter either — see docs/booking-lifecycle.md#7-
/// client-implementations, which pushes payment flows to the web app), so
/// subscribing to a paid plan directs the user to the web checkout instead
/// of duplicating that native-integration surface here.
class SubscriptionRepository {
  SubscriptionRepository(this._dio);

  final Dio _dio;

  Future<List<SubscriptionPlanData>> fetchPlans() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/subscriptions/plans');
      return response.data!
          .map((entry) => SubscriptionPlanData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<MySubscriptionData> fetchMySubscription() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/subscriptions/me');
      return MySubscriptionData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<void> cancelSubscription({String? reason}) async {
    try {
      await _dio.post<void>(
        '/api/v1/subscriptions/me/cancel',
        data: {'reason': ?reason},
      );
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<List<BillingHistoryItemData>> fetchBillingHistory() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/subscriptions/me/billing-history');
      return response.data!
          .map((entry) => BillingHistoryItemData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  SubscriptionException _toException(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return SubscriptionException(data['error']['message'] as String);
    }
    return SubscriptionException(e.message ?? 'Something went wrong. Please try again.');
  }
}
