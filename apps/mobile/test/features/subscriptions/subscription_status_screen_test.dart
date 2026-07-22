import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/subscriptions/subscription_models.dart';
import 'package:mobile/features/subscriptions/subscription_status_screen.dart';

import '../../test_utils/fake_subscription.dart';

const _plan = SubscriptionPlanData(
  id: 'p1',
  name: 'Premium Monthly',
  targetRole: 'customer',
  priceAmount: 199,
  currency: 'INR',
  billingInterval: 'monthly',
  features: {},
);

Future<void> _pump(WidgetTester tester, {FakeSubscriptionRepository? repository}) async {
  final repo = repository ?? FakeSubscriptionRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [subscriptionRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: SubscriptionStatusScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows a free-plan message when there is no active subscription', (tester) async {
    await _pump(tester);

    expect(find.text("You're on the free plan."), findsOneWidget);
    expect(find.text('View plans & upgrade'), findsOneWidget);
  });

  testWidgets('shows the active plan and a cancel button', (tester) async {
    await _pump(
      tester,
      repository: FakeSubscriptionRepository(
        mySubscription: MySubscriptionData(
          subscription: SubscriptionData(
            id: 'sub1',
            plan: _plan,
            status: 'active',
            currentPeriodEnd: DateTime.utc(2026, 8, 1),
            cancelAtPeriodEnd: false,
          ),
          entitlements: const {},
        ),
      ),
    );

    expect(find.text('Premium Monthly'), findsOneWidget);
    expect(find.text('Active'), findsOneWidget);
    expect(find.text('Cancel subscription'), findsOneWidget);
  });

  testWidgets('shows a grace-period warning for a past_due subscription', (tester) async {
    await _pump(
      tester,
      repository: FakeSubscriptionRepository(
        mySubscription: MySubscriptionData(
          subscription: SubscriptionData(
            id: 'sub1',
            plan: _plan,
            status: 'past_due',
            currentPeriodEnd: DateTime.utc(2026, 8, 1),
            cancelAtPeriodEnd: false,
            gracePeriodEndsAt: DateTime.utc(2026, 8, 4),
          ),
          entitlements: const {},
        ),
      ),
    );

    expect(find.textContaining('Your last payment failed'), findsOneWidget);
  });
}
