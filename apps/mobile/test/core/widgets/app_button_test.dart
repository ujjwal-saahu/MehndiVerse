import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_button.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(body: Center(child: child)),
  );
}

void main() {
  group('AppPrimaryButton', () {
    testWidgets('renders its label and responds to taps', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _wrap(AppPrimaryButton(label: 'Continue', onPressed: () => tapped = true)),
      );

      expect(find.text('Continue'), findsOneWidget);
      await tester.tap(find.byType(AppPrimaryButton));
      expect(tapped, isTrue);
    });

    testWidgets('shows a spinner and disables tapping while loading', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _wrap(
          AppPrimaryButton(label: 'Continue', isLoading: true, onPressed: () => tapped = true),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Continue'), findsNothing);

      final button = tester.widget<ElevatedButton>(find.byType(ElevatedButton));
      expect(button.onPressed, isNull);
      expect(tapped, isFalse);
    });

    testWidgets('meets tap target and text contrast accessibility guidelines', (tester) async {
      await tester.pumpWidget(_wrap(AppPrimaryButton(label: 'Continue', onPressed: () {})));

      final handle = tester.ensureSemantics();
      await expectLater(tester, meetsGuideline(textContrastGuideline));
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });
  });

  group('AppSecondaryButton', () {
    testWidgets('renders its label and responds to taps', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _wrap(AppSecondaryButton(label: 'Cancel', onPressed: () => tapped = true)),
      );

      await tester.tap(find.text('Cancel'));
      expect(tapped, isTrue);
    });
  });

  group('AppTextActionButton', () {
    testWidgets('renders its label and responds to taps', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _wrap(AppTextActionButton(label: 'Skip', onPressed: () => tapped = true)),
      );

      await tester.tap(find.text('Skip'));
      expect(tapped, isTrue);
    });
  });
}
