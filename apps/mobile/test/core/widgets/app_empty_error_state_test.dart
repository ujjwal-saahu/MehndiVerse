import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_empty_state.dart';
import 'package:mobile/core/widgets/app_error_state.dart';

Widget wrap(Widget child) {
  return MaterialApp(theme: AppTheme.light, home: Scaffold(body: child));
}

void main() {
  group('AppEmptyState', () {
    testWidgets('renders title and message without an action by default', (tester) async {
      await tester.pumpWidget(
        wrap(const AppEmptyState(title: 'No bookings yet', message: 'Nothing to show here.')),
      );

      expect(find.text('No bookings yet'), findsOneWidget);
      expect(find.text('Nothing to show here.'), findsOneWidget);
      expect(find.byType(ElevatedButton), findsNothing);
    });

    testWidgets('renders an action button when provided', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        wrap(
          AppEmptyState(
            title: 'No bookings yet',
            actionLabel: 'Browse artists',
            onAction: () => tapped = true,
          ),
        ),
      );

      await tester.tap(find.text('Browse artists'));
      expect(tapped, isTrue);
    });
  });

  group('AppErrorState', () {
    testWidgets('renders the error message and a retry button', (tester) async {
      var retried = false;
      await tester.pumpWidget(
        wrap(AppErrorState(message: 'Could not load bookings.', onRetry: () => retried = true)),
      );

      expect(find.text('Something went wrong'), findsOneWidget);
      expect(find.text('Could not load bookings.'), findsOneWidget);

      await tester.tap(find.text('Try again'));
      expect(retried, isTrue);
    });

    testWidgets('omits the retry button when onRetry is not provided', (tester) async {
      await tester.pumpWidget(wrap(const AppErrorState(message: 'Could not load bookings.')));

      expect(find.text('Try again'), findsNothing);
    });
  });
}
