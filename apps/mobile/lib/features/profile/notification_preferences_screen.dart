import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/widgets/widgets.dart';
import 'profile_models.dart';
import 'profile_repository.dart';

class NotificationPreferencesScreen extends ConsumerStatefulWidget {
  const NotificationPreferencesScreen({super.key});

  @override
  ConsumerState<NotificationPreferencesScreen> createState() =>
      _NotificationPreferencesScreenState();
}

class _NotificationPreferencesScreenState
    extends ConsumerState<NotificationPreferencesScreen> {
  late Future<PreferencesData> _preferencesFuture;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _preferencesFuture = ref.read(profileRepositoryProvider).fetchPreferences();
  }

  Future<void> _toggle({
    bool? emailNotifications,
    bool? pushNotifications,
    bool? smsNotifications,
    bool? marketingOptIn,
  }) async {
    try {
      final updated = await ref
          .read(profileRepositoryProvider)
          .updatePreferences(
            emailNotifications: emailNotifications,
            pushNotifications: pushNotifications,
            smsNotifications: smsNotifications,
            marketingOptIn: marketingOptIn,
          );
      setState(() {
        _preferencesFuture = Future.value(updated);
      });
    } on ProfileException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: FutureBuilder<PreferencesData>(
        future: _preferencesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView();
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as ProfileException?)?.message ?? 'Could not load.',
              onRetry: () => setState(_load),
            );
          }

          final prefs = snapshot.data!;
          return ListView(
            children: [
              SwitchListTile(
                key: const Key('pref-email-notifications'),
                title: const Text('Email notifications'),
                value: prefs.emailNotifications,
                onChanged: (value) => _toggle(emailNotifications: value),
              ),
              SwitchListTile(
                key: const Key('pref-push-notifications'),
                title: const Text('Push notifications'),
                value: prefs.pushNotifications,
                onChanged: (value) => _toggle(pushNotifications: value),
              ),
              SwitchListTile(
                key: const Key('pref-sms-notifications'),
                title: const Text('SMS notifications'),
                value: prefs.smsNotifications,
                onChanged: (value) => _toggle(smsNotifications: value),
              ),
              SwitchListTile(
                key: const Key('pref-marketing-opt-in'),
                title: const Text('Marketing emails'),
                subtitle: const Text('Occasional offers and product updates'),
                value: prefs.marketingOptIn,
                onChanged: (value) => _toggle(marketingOptIn: value),
              ),
            ],
          );
        },
      ),
    );
  }
}
