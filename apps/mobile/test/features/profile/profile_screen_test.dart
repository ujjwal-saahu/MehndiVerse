import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/auth/auth_models.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/profile/profile_models.dart';
import 'package:mobile/features/profile/profile_repository.dart';
import 'package:mobile/features/profile/profile_screen.dart';

import '../../test_utils/fake_auth.dart';
import '../../test_utils/fake_profile.dart';

const _user = AuthUser(id: 'u1', email: 'demo@example.com', role: 'customer', status: 'active');

Future<void> _pump(WidgetTester tester, ProfileRepository repository) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(
          (ref) => FakeAuthController(const AuthState.authenticated(_user)),
        ),
        profileRepositoryProvider.overrideWithValue(repository),
      ],
      child: const MaterialApp(home: ProfileScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows the profile after loading', (tester) async {
    final repository = FakeProfileRepository(
      profile: const ProfileData(
        userId: 'u1',
        displayName: 'Demo User',
        bio: 'Loves henna art',
        city: 'Mumbai',
        country: 'IN',
      ),
    );

    await _pump(tester, repository);

    expect(find.text('Demo User'), findsOneWidget);
    expect(find.text('demo@example.com'), findsOneWidget);
    expect(find.text('Loves henna art'), findsOneWidget);
    expect(find.text('Mumbai, IN'), findsOneWidget);
  });

  testWidgets('shows an error state with retry when loading fails', (tester) async {
    final repository = FakeProfileRepository()
      ..fetchProfileError = ProfileException('Network error.');

    await _pump(tester, repository);

    expect(find.text('Network error.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('shows edit profile and settings actions', (tester) async {
    final repository = FakeProfileRepository();

    await _pump(tester, repository);

    expect(find.text('Edit profile'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
  });
}
