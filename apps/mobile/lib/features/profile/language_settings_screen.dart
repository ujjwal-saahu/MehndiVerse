import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/widgets/widgets.dart';
import 'profile_models.dart';
import 'profile_repository.dart';

const _availableLanguages = <String, String>{
  'en': 'English',
  'hi': 'Hindi (हिन्दी)',
  'mr': 'Marathi (मराठी)',
  'gu': 'Gujarati (ગુજરાતી)',
  'ta': 'Tamil (தமிழ்)',
};

class LanguageSettingsScreen extends ConsumerStatefulWidget {
  const LanguageSettingsScreen({super.key});

  @override
  ConsumerState<LanguageSettingsScreen> createState() => _LanguageSettingsScreenState();
}

class _LanguageSettingsScreenState extends ConsumerState<LanguageSettingsScreen> {
  late Future<ProfileData> _profileFuture;
  String? _pendingSelection;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _profileFuture = ref.read(profileRepositoryProvider).fetchProfile();
  }

  Future<void> _select(String code) async {
    setState(() {
      _pendingSelection = code;
      _isSaving = true;
    });
    try {
      await ref.read(profileRepositoryProvider).updateProfile(locale: code);
      if (mounted) AppSnackBar.showSuccess(context, 'Language updated.');
    } on ProfileException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Language')),
      body: FutureBuilder<ProfileData>(
        future: _profileFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView();
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as ProfileException?)?.message ?? 'Could not load.',
              onRetry: () => setState(() {
                _profileFuture = ref.read(profileRepositoryProvider).fetchProfile();
              }),
            );
          }

          final currentLocale = _pendingSelection ?? snapshot.data!.locale ?? 'en';
          return RadioGroup<String>(
            groupValue: currentLocale,
            onChanged: (value) {
              if (!_isSaving && value != null) _select(value);
            },
            child: ListView(
              children: _availableLanguages.entries.map((entry) {
                return RadioListTile<String>(value: entry.key, title: Text(entry.value));
              }).toList(),
            ),
          );
        },
      ),
    );
  }
}
