import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'subscription_models.dart';
import 'subscription_repository.dart';

const Map<String, String> _statusLabels = {
  'active': 'Active',
  'cancelled': 'Cancelled',
  'expired': 'Expired',
  'past_due': 'Payment overdue — grace period',
  'trialing': 'Awaiting first payment',
};

class SubscriptionStatusScreen extends ConsumerStatefulWidget {
  const SubscriptionStatusScreen({super.key});

  @override
  ConsumerState<SubscriptionStatusScreen> createState() => _SubscriptionStatusScreenState();
}

class _SubscriptionStatusScreenState extends ConsumerState<SubscriptionStatusScreen> {
  Future<MySubscriptionData>? _future;
  List<BillingHistoryItemData> _billingHistory = [];
  bool _isCancelling = false;
  String? _cancelError;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final repository = ref.read(subscriptionRepositoryProvider);
    setState(() {
      _future = repository.fetchMySubscription();
    });
    repository
        .fetchBillingHistory()
        .then((items) {
          if (mounted) setState(() => _billingHistory = items);
        })
        .catchError((Object _) {});
  }

  Future<void> _cancel() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel subscription'),
        content: const Text(
          "You'll keep access until the current period ends.",
        ),
        actions: [
          TextButton(onPressed: () => context.pop(false), child: const Text('Keep it')),
          TextButton(onPressed: () => context.pop(true), child: const Text('Cancel it')),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() {
      _isCancelling = true;
      _cancelError = null;
    });
    try {
      await ref.read(subscriptionRepositoryProvider).cancelSubscription();
      _load();
    } on SubscriptionException catch (e) {
      setState(() => _cancelError = e.message);
    } finally {
      if (mounted) setState(() => _isCancelling = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My subscription')),
      body: FutureBuilder<MySubscriptionData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading your subscription…');
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return AppErrorState(
              message: error is SubscriptionException
                  ? error.message
                  : 'Could not load your subscription.',
              onRetry: _load,
            );
          }

          final data = snapshot.data!;
          final subscription = data.subscription;

          return ListView(
            padding: const EdgeInsets.all(Spacing.s4),
            children: [
              if (subscription != null) ...[
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        subscription.plan.name,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: Spacing.s1),
                      Text(_statusLabels[subscription.status] ?? subscription.status),
                      const SizedBox(height: Spacing.s1),
                      Text(
                        subscription.cancelAtPeriodEnd
                            ? 'Access ends ${_formatDate(subscription.currentPeriodEnd)}'
                            : 'Renews ${_formatDate(subscription.currentPeriodEnd)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      if (subscription.status == 'past_due' &&
                          subscription.gracePeriodEndsAt != null)
                        Padding(
                          padding: const EdgeInsets.only(top: Spacing.s2),
                          child: Text(
                            'Your last payment failed. Retry before '
                            '${_formatDate(subscription.gracePeriodEndsAt!)} to keep your '
                            'benefits.',
                            style: TextStyle(color: Theme.of(context).colorScheme.error),
                          ),
                        ),
                      if (_cancelError != null)
                        Padding(
                          padding: const EdgeInsets.only(top: Spacing.s2),
                          child: Text(
                            _cancelError!,
                            style: TextStyle(color: Theme.of(context).colorScheme.error),
                          ),
                        ),
                      if (!subscription.cancelAtPeriodEnd &&
                          (subscription.status == 'active' ||
                              subscription.status == 'past_due')) ...[
                        const SizedBox(height: Spacing.s3),
                        AppSecondaryButton(
                          label: 'Cancel subscription',
                          onPressed: _cancel,
                          isLoading: _isCancelling,
                        ),
                      ],
                    ],
                  ),
                ),
              ] else ...[
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("You're on the free plan."),
                      const SizedBox(height: Spacing.s3),
                      AppSecondaryButton(
                        label: 'View plans & upgrade',
                        onPressed: () => context.push('/subscription/plans'),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: Spacing.s4),
              Text('Billing history', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: Spacing.s2),
              if (_billingHistory.isEmpty)
                const Text('No subscription payments yet.')
              else
                for (final item in _billingHistory)
                  Padding(
                    padding: const EdgeInsets.only(bottom: Spacing.s2),
                    child: AppCard(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              '${item.planName ?? 'Subscription'} — '
                              '${item.currency} ${(item.amount / 100).toStringAsFixed(2)}',
                            ),
                          ),
                          Text(item.status, style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }

  String _formatDate(DateTime date) => '${date.year}-${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';
}
