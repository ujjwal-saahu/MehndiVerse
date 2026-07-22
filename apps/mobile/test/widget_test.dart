import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/auth/auth_models.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/main.dart';

import 'test_utils/fake_auth.dart';
import 'test_utils/fake_gallery.dart';
import 'test_utils/fake_profile.dart';

const _customer = AuthUser(
  id: 'u1',
  email: 'demo@example.com',
  role: 'customer',
  status: 'active',
);
const _artist = AuthUser(
  id: 'u2',
  email: 'artist@example.com',
  role: 'artist',
  status: 'active',
);

Future<void> _pumpApp(WidgetTester tester, AuthState authState) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authControllerProvider.overrideWith((ref) => FakeAuthController(authState)),
        profileRepositoryProvider.overrideWithValue(FakeProfileRepository()),
        galleryRepositoryProvider.overrideWithValue(FakeGalleryRepository()),
      ],
      child: const MehndiVerseApp(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('unauthenticated app boot redirects to the login screen', (
    WidgetTester tester,
  ) async {
    await _pumpApp(tester, const AuthState.unauthenticated());

    expect(find.text('Log in'), findsWidgets);
    expect(find.byKey(const Key('login-email-field')), findsOneWidget);
  });

  testWidgets('authenticated customer sees the customer bottom navigation', (
    WidgetTester tester,
  ) async {
    await _pumpApp(tester, const AuthState.authenticated(_customer));

    expect(find.byType(NavigationBar), findsOneWidget);
    // IndexedStack builds every branch, so the Discover tab's title shows up
    // in both its AppBar and the nav bar label, plus each placeholder tab's
    // title shows up in both its AppBar and body.
    expect(find.text('Discover'), findsWidgets);
    expect(find.text('No designs yet'), findsOneWidget);
    expect(find.text('Collections'), findsWidgets);
    expect(find.text('Bookings'), findsWidgets);
    expect(find.text('Dashboard'), findsNothing);
  });

  testWidgets('authenticated artist sees the artist bottom navigation', (
    WidgetTester tester,
  ) async {
    await _pumpApp(tester, const AuthState.authenticated(_artist));

    expect(find.text('Dashboard'), findsWidgets);
    expect(find.text('Portfolio'), findsOneWidget);
    expect(find.text('Discover'), findsNothing);
  });

  testWidgets('customer can switch tabs via the bottom navigation', (WidgetTester tester) async {
    await _pumpApp(tester, const AuthState.authenticated(_customer));

    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();

    expect(find.text('demo@example.com'), findsOneWidget);
  });

  testWidgets('logout from the profile tab returns to the login screen', (
    WidgetTester tester,
  ) async {
    await _pumpApp(tester, const AuthState.authenticated(_customer));

    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Log out').last);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('login-email-field')), findsOneWidget);
  });
}
