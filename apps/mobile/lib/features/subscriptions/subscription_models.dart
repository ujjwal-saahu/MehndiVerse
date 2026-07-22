/// Mirrors app/schemas/subscription.py — see
/// docs/subscriptions-and-entitlements.md. `priceAmount` is a decimal major
/// unit (a human-facing list price), unlike booking payments' integer minor
/// units — see docs/payments.md#7-integer-minor-currency-units.
class SubscriptionPlanData {
  const SubscriptionPlanData({
    required this.id,
    required this.name,
    required this.targetRole,
    required this.priceAmount,
    required this.currency,
    required this.billingInterval,
    required this.features,
  });

  final String id;
  final String name;
  final String targetRole;
  final double priceAmount;
  final String currency;
  final String billingInterval;
  final Map<String, dynamic> features;

  factory SubscriptionPlanData.fromJson(Map<String, dynamic> json) {
    return SubscriptionPlanData(
      id: json['id'] as String,
      name: json['name'] as String,
      targetRole: json['target_role'] as String,
      priceAmount: (json['price_amount'] as num).toDouble(),
      currency: json['currency'] as String,
      billingInterval: json['billing_interval'] as String,
      features: (json['features'] as Map<String, dynamic>?) ?? const {},
    );
  }
}

class SubscriptionData {
  const SubscriptionData({
    required this.id,
    required this.plan,
    required this.status,
    required this.currentPeriodEnd,
    required this.cancelAtPeriodEnd,
    this.gracePeriodEndsAt,
  });

  final String id;
  final SubscriptionPlanData plan;
  final String status;
  final DateTime currentPeriodEnd;
  final bool cancelAtPeriodEnd;
  final DateTime? gracePeriodEndsAt;

  factory SubscriptionData.fromJson(Map<String, dynamic> json) {
    return SubscriptionData(
      id: json['id'] as String,
      plan: SubscriptionPlanData.fromJson(json['plan'] as Map<String, dynamic>),
      status: json['status'] as String,
      currentPeriodEnd: DateTime.parse(json['current_period_end'] as String),
      cancelAtPeriodEnd: json['cancel_at_period_end'] as bool,
      gracePeriodEndsAt: json['grace_period_ends_at'] == null
          ? null
          : DateTime.parse(json['grace_period_ends_at'] as String),
    );
  }
}

class MySubscriptionData {
  const MySubscriptionData({required this.subscription, required this.entitlements});

  final SubscriptionData? subscription;
  final Map<String, dynamic> entitlements;

  factory MySubscriptionData.fromJson(Map<String, dynamic> json) {
    return MySubscriptionData(
      subscription: json['subscription'] == null
          ? null
          : SubscriptionData.fromJson(json['subscription'] as Map<String, dynamic>),
      entitlements: (json['entitlements'] as Map<String, dynamic>?) ?? const {},
    );
  }
}

class BillingHistoryItemData {
  const BillingHistoryItemData({
    required this.paymentId,
    this.planName,
    required this.amount,
    required this.currency,
    required this.status,
    this.failureReason,
    required this.createdAt,
  });

  final String paymentId;
  final String? planName;
  final int amount;
  final String currency;
  final String status;
  final String? failureReason;
  final DateTime createdAt;

  factory BillingHistoryItemData.fromJson(Map<String, dynamic> json) {
    return BillingHistoryItemData(
      paymentId: json['payment_id'] as String,
      planName: json['plan_name'] as String?,
      amount: json['amount'] as int,
      currency: json['currency'] as String,
      status: json['status'] as String,
      failureReason: json['failure_reason'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
