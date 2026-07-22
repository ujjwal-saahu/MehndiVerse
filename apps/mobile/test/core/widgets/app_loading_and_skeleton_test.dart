import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_loading_indicator.dart';
import 'package:mobile/core/widgets/app_skeleton.dart';

Widget wrap(Widget child) {
  return MaterialApp(theme: AppTheme.light, home: Scaffold(body: child));
}

void main() {
  testWidgets('AppLoadingIndicator renders a spinner', (tester) async {
    await tester.pumpWidget(wrap(const AppLoadingIndicator()));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('AppLoadingView renders a spinner with an optional message', (tester) async {
    await tester.pumpWidget(wrap(const AppLoadingView(message: 'Loading your bookings…')));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Loading your bookings…'), findsOneWidget);
  });

  testWidgets('AppSkeleton renders and exposes a loading semantics label', (tester) async {
    await tester.pumpWidget(wrap(const AppSkeleton(width: 120)));
    await tester.pump(const Duration(milliseconds: 100));

    final handle = tester.ensureSemantics();
    expect(find.bySemanticsLabel('Loading'), findsOneWidget);
    handle.dispose();
  });

  testWidgets('AppSkeleton.circle renders at the requested diameter', (tester) async {
    await tester.pumpWidget(wrap(const AppSkeleton.circle(diameter: 48)));

    final size = tester.getSize(find.byType(Container));
    expect(size, const Size(48, 48));
  });
}
