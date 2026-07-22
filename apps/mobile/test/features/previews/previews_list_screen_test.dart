import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/previews/preview_repository.dart';
import 'package:mobile/features/previews/previews_list_screen.dart';

import '../../test_utils/fake_preview.dart';

Future<void> _pump(WidgetTester tester, {FakePreviewRepository? repository}) async {
  final repo = repository ?? FakePreviewRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [previewRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: PreviewsListScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows an empty state when there are no previews', (tester) async {
    await _pump(tester);

    expect(find.text('No previews yet'), findsOneWidget);
  });

  testWidgets('shows a retry-capable error state when loading fails', (tester) async {
    await _pump(
      tester,
      repository: FakePreviewRepository(
        fetchMineError: PreviewException('Could not load previews.'),
      ),
    );

    expect(find.text('Could not load previews.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  // Rendering a saved preview's thumbnail goes through Image.network, which
  // this test suite has no mocking solution for yet (flutter_test's
  // HttpOverrides always returns 400) — same gap as every other screen
  // here that renders a real network image, none of which are exercised
  // in a widget test either. Empty/error states above cover the rest of
  // this screen's logic without hitting that gap.
}
