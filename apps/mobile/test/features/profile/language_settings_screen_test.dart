import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/profile/language_settings_screen.dart';
import 'package:mobile/features/profile/profile_models.dart';

import '../../test_utils/fake_profile.dart';

void main() {
  testWidgets('selecting a language saves it via the repository', (tester) async {
    final repository = FakeProfileRepository(
      profile: const ProfileData(userId: 'u1', displayName: 'Demo User', locale: 'en'),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: LanguageSettingsScreen()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Hindi (हिन्दी)'));
    await tester.pumpAndSettle();

    expect(repository.profile.locale, 'hi');
  });
}
