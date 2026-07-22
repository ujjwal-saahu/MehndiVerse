import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/widgets/widgets.dart';
import 'profile_models.dart';
import 'profile_repository.dart';

class PrivacySettingsScreen extends ConsumerStatefulWidget {
  const PrivacySettingsScreen({super.key});

  @override
  ConsumerState<PrivacySettingsScreen> createState() => _PrivacySettingsScreenState();
}

class _PrivacySettingsScreenState extends ConsumerState<PrivacySettingsScreen> {
  late Future<PreferencesData> _preferencesFuture;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _preferencesFuture = ref.read(profileRepositoryProvider).fetchPreferences();
  }

  Future<void> _update({
    String? profileVisibility,
    bool? showLocation,
    bool? allowMessagesFromStrangers,
  }) async {
    try {
      final updated = await ref
          .read(profileRepositoryProvider)
          .updatePreferences(
            profileVisibility: profileVisibility,
            showLocation: showLocation,
            allowMessagesFromStrangers: allowMessagesFromStrangers,
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
      appBar: AppBar(title: const Text('Privacy')),
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
                key: const Key('privacy-profile-private'),
                title: const Text('Private profile'),
                subtitle: const Text('Only you and staff can view your profile'),
                value: prefs.isPrivate,
                onChanged: (value) =>
                    _update(profileVisibility: value ? 'private' : 'public'),
              ),
              SwitchListTile(
                key: const Key('privacy-show-location'),
                title: const Text('Show my location'),
                subtitle: const Text('City and country shown to other people'),
                value: prefs.showLocation,
                onChanged: (value) => _update(showLocation: value),
              ),
              SwitchListTile(
                key: const Key('privacy-allow-messages-from-strangers'),
                title: const Text('Allow messages from anyone'),
                subtitle: const Text('Turn off to only receive messages related to your bookings'),
                value: prefs.allowMessagesFromStrangers,
                onChanged: (value) => _update(allowMessagesFromStrangers: value),
              ),
              const Divider(),
              ListTile(
                leading: const Icon(Icons.block),
                title: const Text('Blocked users'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push('/settings/blocked-users'),
              ),
            ],
          );
        },
      ),
    );
  }
}
