import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/profile/privacy_settings_screen.dart';

import '../../test_utils/fake_profile.dart';

void main() {
  testWidgets('turning on private profile updates preferences', (tester) async {
    final repository = FakeProfileRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: PrivacySettingsScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(repository.preferences.profileVisibility, 'public');

    await tester.tap(find.byKey(const Key('privacy-profile-private')));
    await tester.pumpAndSettle();

    expect(repository.preferences.profileVisibility, 'private');
  });

  testWidgets('links through to the blocked users screen', (tester) async {
    final repository = FakeProfileRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileRepositoryProvider.overrideWithValue(repository)],
        child: MaterialApp(
          onGenerateRoute: (settings) {
            return MaterialPageRoute(builder: (_) => const PrivacySettingsScreen());
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Blocked users'), findsOneWidget);
  });
}
