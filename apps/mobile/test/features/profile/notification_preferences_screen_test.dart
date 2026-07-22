import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/profile/notification_preferences_screen.dart';

import '../../test_utils/fake_profile.dart';

void main() {
  testWidgets('toggling a switch persists the change via the repository', (tester) async {
    final repository = FakeProfileRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: NotificationPreferencesScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(repository.preferences.pushNotifications, isTrue);

    await tester.tap(find.byKey(const Key('pref-push-notifications')));
    await tester.pumpAndSettle();

    expect(repository.preferences.pushNotifications, isFalse);
    expect(
      tester.widget<SwitchListTile>(find.byKey(const Key('pref-push-notifications'))).value,
      isFalse,
    );
  });
}
