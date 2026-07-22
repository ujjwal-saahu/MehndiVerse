import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/previews/preview_studio_screen.dart';

import '../../test_utils/fake_preview.dart';

void main() {
  testWidgets('explains storage behavior and prompts for a photo before anything is saved', (
    tester,
  ) async {
    // The screen's content is taller than the default test surface, and
    // ListView only builds children within the viewport + cache extent —
    // grow the surface so every section is actually built and findable
    // (mirrors gallery/design_detail_screen_test.dart's same fix).
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [previewRepositoryProvider.overrideWithValue(FakePreviewRepository())],
        child: const MaterialApp(home: PreviewStudioScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Your photo stays on this device'), findsOneWidget);
    expect(find.text('Choose a hand or foot photo'), findsOneWidget);
    expect(find.text('Save preview'), findsOneWidget);

    // No design has been chosen yet, so the overlay controls (flip/
    // opacity/reset) shouldn't be shown at all.
    expect(find.text('Flip overlay'), findsNothing);
  });
}
