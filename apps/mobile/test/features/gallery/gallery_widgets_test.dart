import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_widgets.dart';

const _designWithArtist = DesignSummaryData(
  id: 'd1',
  artistDisplayName: 'Asha',
  title: 'Bridal Special',
  isFeatured: false,
  isPremium: false,
  viewCount: 3,
);

const _designWithoutImage = DesignSummaryData(
  id: 'd2',
  title: 'Processing Design',
  isFeatured: false,
  isPremium: false,
  viewCount: 0,
);

void main() {
  testWidgets('DesignThumbnailCard exposes an accessible image description', (tester) async {
    final handle = tester.ensureSemantics();

    await tester.pumpWidget(
      MaterialApp.router(
        routerConfig: GoRouter(
          routes: [
            GoRoute(
              path: '/',
              builder: (context, state) =>
                  const Scaffold(body: DesignThumbnailCard(design: _designWithArtist)),
            ),
            GoRoute(
              path: '/design/:id',
              builder: (context, state) => const Scaffold(body: Text('Design detail')),
            ),
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.bySemanticsLabel('Bridal Special mehndi design by Asha'),
      findsOneWidget,
    );
    handle.dispose();
  });

  testWidgets('DesignThumbnailCard shows a placeholder icon when there is no thumbnail', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: DesignThumbnailCard(design: _designWithoutImage))),
    );

    expect(find.byIcon(Icons.image_outlined), findsOneWidget);
  });

  testWidgets('CategoryChipsRow marks the active chip as selected', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CategoryChipsRow(
            categories: const [
              CategoryData(id: 'c1', name: 'Bridal', slug: 'bridal', categoryType: 'occasion'),
            ],
            activeKey: 'c1',
            onSelect: (_) {},
          ),
        ),
      ),
    );

    final chip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Bridal'));
    expect(chip.selected, isTrue);
  });
}
