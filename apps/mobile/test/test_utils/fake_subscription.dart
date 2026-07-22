import 'package:mobile/features/subscriptions/subscription_models.dart';
import 'package:mobile/features/subscriptions/subscription_repository.dart';

/// In-memory stand-in for [SubscriptionRepository] — mirrors
/// test_utils/fake_gallery.dart's approach.
class FakeSubscriptionRepository implements SubscriptionRepository {
  FakeSubscriptionRepository({
    List<SubscriptionPlanData>? plans,
    this.mySubscription,
    List<BillingHistoryItemData>? billingHistory,
    this.plansError,
    this.mySubscriptionError,
    this.cancelError,
  }) : plans = plans ?? [],
       billingHistory = billingHistory ?? [];

  List<SubscriptionPlanData> plans;
  MySubscriptionData? mySubscription;
  List<BillingHistoryItemData> billingHistory;
  SubscriptionException? plansError;
  SubscriptionException? mySubscriptionError;
  SubscriptionException? cancelError;
  int cancelCallCount = 0;

  @override
  Future<List<SubscriptionPlanData>> fetchPlans() async {
    if (plansError != null) throw plansError!;
    return plans;
  }

  @override
  Future<MySubscriptionData> fetchMySubscription() async {
    if (mySubscriptionError != null) throw mySubscriptionError!;
    return mySubscription ?? const MySubscriptionData(subscription: null, entitlements: {});
  }

  @override
  Future<void> cancelSubscription({String? reason}) async {
    cancelCallCount += 1;
    if (cancelError != null) throw cancelError!;
  }

  @override
  Future<List<BillingHistoryItemData>> fetchBillingHistory() async => billingHistory;
}
