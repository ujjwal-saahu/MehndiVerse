import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/profile/edit_profile_screen.dart';
import 'package:mobile/features/profile/profile_models.dart';

import '../../test_utils/fake_profile.dart';

Future<FakeProfileRepository> _pump(WidgetTester tester) async {
  final repository = FakeProfileRepository(
    profile: const ProfileData(userId: 'u1', displayName: 'Original Name', bio: 'Original bio'),
  );
  await tester.pumpWidget(
    ProviderScope(
      overrides: [profileRepositoryProvider.overrideWithValue(repository)],
      child: const MaterialApp(home: EditProfileScreen()),
    ),
  );
  await tester.pumpAndSettle();
  return repository;
}

void main() {
  testWidgets('pre-fills the form with the current profile', (tester) async {
    await _pump(tester);

    expect(find.widgetWithText(TextFormField, 'Original Name'), findsOneWidget);
  });

  testWidgets('rejects a blank display name', (tester) async {
    await _pump(tester);

    await tester.enterText(find.byKey(const Key('edit-profile-display-name-field')), '   ');
    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();

    expect(find.text('Display name is required.'), findsOneWidget);
  });

  testWidgets('saves changes and pops the screen', (tester) async {
    final repository = await _pump(tester);

    await tester.enterText(
      find.byKey(const Key('edit-profile-display-name-field')),
      'Updated Name',
    );
    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();

    expect(repository.profile.displayName, 'Updated Name');
  });
}
