import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_dialog.dart';

void main() {
  Widget wrap(void Function(BuildContext) onPressed) {
    return MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(
        body: Builder(
          builder: (context) => ElevatedButton(
            onPressed: () => onPressed(context),
            child: const Text('Open'),
          ),
        ),
      ),
    );
  }

  testWidgets('returns true when the user confirms', (tester) async {
    bool? result;
    await tester.pumpWidget(
      wrap((context) async {
        result = await showAppConfirmDialog(
          context,
          title: 'Delete item',
          message: 'Are you sure?',
          confirmLabel: 'Delete',
        );
      }),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    expect(find.text('Delete item'), findsOneWidget);
    expect(find.text('Are you sure?'), findsOneWidget);

    await tester.tap(find.text('Delete'));
    await tester.pumpAndSettle();

    expect(result, isTrue);
  });

  testWidgets('returns false when the user cancels', (tester) async {
    bool? result;
    await tester.pumpWidget(
      wrap((context) async {
        result = await showAppConfirmDialog(
          context,
          title: 'Delete item',
          message: 'Are you sure?',
        );
      }),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(result, isFalse);
  });
}
