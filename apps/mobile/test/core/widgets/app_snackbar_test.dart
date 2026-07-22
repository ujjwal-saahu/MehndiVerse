import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_snackbar.dart';

void main() {
  Widget wrap(void Function(BuildContext) onPressed) {
    return MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(
        body: Builder(
          builder: (context) => ElevatedButton(
            onPressed: () => onPressed(context),
            child: const Text('Trigger'),
          ),
        ),
      ),
    );
  }

  testWidgets('showSuccess displays the message in a SnackBar', (tester) async {
    await tester.pumpWidget(
      wrap((context) => AppSnackBar.showSuccess(context, 'Booking confirmed')),
    );

    await tester.tap(find.text('Trigger'));
    await tester.pump();

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('Booking confirmed'), findsOneWidget);
  });

  testWidgets('showError displays the message in a SnackBar', (tester) async {
    await tester.pumpWidget(wrap((context) => AppSnackBar.showError(context, 'Something failed')));

    await tester.tap(find.text('Trigger'));
    await tester.pump();

    expect(find.text('Something failed'), findsOneWidget);
  });

  testWidgets('a second snackbar replaces the first rather than stacking', (tester) async {
    await tester.pumpWidget(
      wrap((context) {
        AppSnackBar.showInfo(context, 'First message');
        AppSnackBar.showInfo(context, 'Second message');
      }),
    );

    await tester.tap(find.text('Trigger'));
    await tester.pump();

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('Second message'), findsOneWidget);
  });
}
