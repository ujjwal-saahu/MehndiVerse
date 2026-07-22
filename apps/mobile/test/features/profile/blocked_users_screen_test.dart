import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/profile/blocked_users_screen.dart';
import 'package:mobile/features/profile/profile_models.dart';

import '../../test_utils/fake_profile.dart';

void main() {
  testWidgets('shows an empty state when nobody is blocked', (tester) async {
    final repository = FakeProfileRepository(blockedUsers: []);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: BlockedUsersScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('No blocked users'), findsOneWidget);
  });

  testWidgets('lists blocked users and unblocks on tap', (tester) async {
    final repository = FakeProfileRepository(
      blockedUsers: const [BlockedUser(userId: 'u2', displayName: 'Annoying Person')],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: BlockedUsersScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Annoying Person'), findsOneWidget);

    await tester.tap(find.text('Unblock'));
    await tester.pumpAndSettle();

    expect(repository.blockedUsers, isEmpty);
    expect(find.text('No blocked users'), findsOneWidget);
  });
}
