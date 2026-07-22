import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_card.dart';

Widget _wrap(Widget child) {
  return MaterialApp(theme: AppTheme.light, home: Scaffold(body: child));
}

void main() {
  testWidgets('renders its child content', (tester) async {
    await tester.pumpWidget(_wrap(const AppCard(child: Text('Card content'))));

    expect(find.text('Card content'), findsOneWidget);
  });

  testWidgets('is tappable when onTap is provided', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      _wrap(AppCard(onTap: () => tapped = true, child: const Text('Tappable card'))),
    );

    await tester.tap(find.byType(InkWell));
    expect(tapped, isTrue);
  });

  testWidgets('is not wrapped in InkWell when onTap is absent', (tester) async {
    await tester.pumpWidget(_wrap(const AppCard(child: Text('Static card'))));

    expect(find.byType(InkWell), findsNothing);
  });
}
