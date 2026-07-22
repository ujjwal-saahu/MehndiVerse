import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/subscriptions/plans_screen.dart';
import 'package:mobile/features/subscriptions/subscription_models.dart';
import 'package:mobile/features/subscriptions/subscription_repository.dart';

import '../../test_utils/fake_subscription.dart';

const _plan = SubscriptionPlanData(
  id: 'p1',
  name: 'Premium Monthly',
  targetRole: 'customer',
  priceAmount: 199,
  currency: 'INR',
  billingInterval: 'monthly',
  features: {'premium_design_access': true, 'download_limit_per_month': 100},
);

Future<void> _pump(WidgetTester tester, {FakeSubscriptionRepository? repository}) async {
  final repo = repository ?? FakeSubscriptionRepository(plans: const [_plan]);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [subscriptionRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: PlansScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows plan name, price, and features once loaded', (tester) async {
    await _pump(tester);

    expect(find.text('Premium Monthly'), findsOneWidget);
    expect(find.text('INR 199.00/month'), findsOneWidget);
    expect(find.text('• Access to premium designs'), findsOneWidget);
    expect(find.text('• 100 downloads / month'), findsOneWidget);
  });

  testWidgets('shows an empty state when there are no plans', (tester) async {
    await _pump(tester, repository: FakeSubscriptionRepository());

    expect(find.text('No plans available'), findsOneWidget);
  });

  testWidgets('shows a retry-capable error state when plans fail to load', (tester) async {
    await _pump(
      tester,
      repository: FakeSubscriptionRepository(
        plansError: SubscriptionException('Could not load plans.'),
      ),
    );

    expect(find.text('Could not load plans.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });
}
