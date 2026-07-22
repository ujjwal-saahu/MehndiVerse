import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/widgets/app_text_field.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(body: Padding(padding: const EdgeInsets.all(16), child: child)),
  );
}

void main() {
  testWidgets('renders its label and accepts input', (tester) async {
    final controller = TextEditingController();
    await tester.pumpWidget(_wrap(AppTextField(label: 'Email', controller: controller)));

    expect(find.text('Email'), findsOneWidget);

    await tester.enterText(find.byType(AppTextField), 'person@example.com');
    expect(controller.text, 'person@example.com');
  });

  testWidgets('shows validation errors from the validator', (tester) async {
    final formKey = GlobalKey<FormState>();
    await tester.pumpWidget(
      _wrap(
        Form(
          key: formKey,
          child: AppTextField(
            label: 'Email',
            validator: (value) => (value == null || value.isEmpty) ? 'Required' : null,
          ),
        ),
      ),
    );

    expect(formKey.currentState!.validate(), isFalse);
    await tester.pump();

    expect(find.text('Required'), findsOneWidget);
  });

  testWidgets('displays an externally supplied error message', (tester) async {
    await tester.pumpWidget(_wrap(const AppTextField(label: 'Email', errorText: 'Invalid email')));

    expect(find.text('Invalid email'), findsOneWidget);
  });
}
