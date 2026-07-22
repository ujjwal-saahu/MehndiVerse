import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/auth/login_screen.dart';

import '../../test_utils/fake_auth.dart';
import 'package:mobile/core/auth/auth_models.dart';
import 'package:mobile/core/providers.dart';

Widget _wrap() {
  return ProviderScope(
    overrides: [
      authControllerProvider.overrideWith(
        (ref) => FakeAuthController(const AuthState.unauthenticated()),
      ),
    ],
    child: MaterialApp(theme: AppTheme.light, home: const LoginScreen()),
  );
}

void main() {
  testWidgets('shows validation errors for empty submission', (tester) async {
    await tester.pumpWidget(_wrap());

    await tester.tap(find.widgetWithText(ElevatedButton, 'Log in'));
    await tester.pump();

    expect(find.text('Email is required.'), findsOneWidget);
    expect(find.text('Password is required.'), findsOneWidget);
  });

  testWidgets('meets text contrast and labeled tap target accessibility guidelines', (
    tester,
  ) async {
    await tester.pumpWidget(_wrap());

    final handle = tester.ensureSemantics();
    await expectLater(tester, meetsGuideline(textContrastGuideline));
    await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
    handle.dispose();
  });
}
