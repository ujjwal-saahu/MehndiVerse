import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'subscription_models.dart';
import 'subscription_repository.dart';

/// Plan browsing — see docs/subscriptions-and-entitlements.md. Checkout
/// itself is deferred to the web app (mehndiverse.com/pricing): no payment
/// SDK exists anywhere in this app yet, so subscribing here would mean
/// adding native Razorpay integration just for this one flow. See
/// SubscriptionRepository's doc comment.
class PlansScreen extends ConsumerStatefulWidget {
  const PlansScreen({super.key});

  @override
  ConsumerState<PlansScreen> createState() => _PlansScreenState();
}

class _PlansScreenState extends ConsumerState<PlansScreen> {
  Future<List<SubscriptionPlanData>>? _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() {
      _future = ref.read(subscriptionRepositoryProvider).fetchPlans();
    });
  }

  String _formatPrice(SubscriptionPlanData plan) {
    if (plan.priceAmount <= 0) return 'Free';
    final perInterval = plan.billingInterval == 'yearly' ? '/year' : '/month';
    return '${plan.currency} ${plan.priceAmount.toStringAsFixed(2)}$perInterval';
  }

  List<String> _featureLines(Map<String, dynamic> features) {
    final lines = <String>[];
    if (features['premium_design_access'] == true) lines.add('Access to premium designs');
    final downloadLimit = features['download_limit_per_month'];
    if (downloadLimit is num) lines.add('$downloadLimit downloads / month');
    final aiCredits = features['ai_credits_per_month'];
    if (aiCredits is num) lines.add('$aiCredits AI credits / month');
    final portfolioLimit = features['portfolio_limit'];
    if (portfolioLimit == null && features.containsKey('portfolio_limit')) {
      lines.add('Unlimited portfolio designs');
    } else if (portfolioLimit is num) {
      lines.add('Up to $portfolioLimit published designs');
    }
    return lines;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Plans & pricing')),
      body: FutureBuilder<List<SubscriptionPlanData>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading plans…');
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return AppErrorState(
              message: error is SubscriptionException ? error.message : 'Could not load plans.',
              onRetry: _load,
            );
          }

          final plans = snapshot.data!;
          if (plans.isEmpty) {
            return const AppEmptyState(title: 'No plans available');
          }

          return ListView.separated(
            padding: const EdgeInsets.all(Spacing.s4),
            itemCount: plans.length,
            separatorBuilder: (context, index) => const SizedBox(height: Spacing.s3),
            itemBuilder: (context, index) {
              final plan = plans[index];
              return AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(plan.name, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: Spacing.s1),
                    Text(_formatPrice(plan), style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: Spacing.s2),
                    for (final line in _featureLines(plan.features))
                      Padding(
                        padding: const EdgeInsets.only(top: Spacing.s1),
                        child: Text('• $line'),
                      ),
                    if (plan.priceAmount > 0) ...[
                      const SizedBox(height: Spacing.s3),
                      Text(
                        'Subscribe from mehndiverse.com/pricing on the web.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}
