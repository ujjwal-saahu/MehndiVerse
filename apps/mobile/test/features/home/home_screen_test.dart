import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';
import 'package:mobile/features/home/home_screen.dart';

import '../../test_utils/fake_gallery.dart';

const _design = DesignSummaryData(
  id: 'd1',
  artistDisplayName: 'Asha',
  title: 'Bridal Special',
  isFeatured: false,
  isPremium: false,
  thumbnailUrl: null,
  viewCount: 3,
);

const _category = CategoryData(id: 'c1', name: 'Bridal', slug: 'bridal', categoryType: 'occasion');

Future<FakeGalleryRepository> _pump(
  WidgetTester tester, {
  FakeGalleryRepository? repository,
}) async {
  // The browse view's "Load more" button sits below the grid, taller than
  // the default test surface — grow it so ListView actually builds (and
  // `find` can see) content below the fold. See the equivalent comment in
  // design_detail_screen_test.dart.
  tester.view.physicalSize = const Size(800, 2000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final repo = repository ?? FakeGalleryRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [galleryRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: HomeScreen()),
    ),
  );
  await tester.pumpAndSettle();
  return repo;
}

void main() {
  testWidgets('shows an empty state when the home feed has no designs', (tester) async {
    await _pump(tester);

    expect(find.text('No designs yet'), findsOneWidget);
  });

  testWidgets('shows the Latest section once the home feed loads', (tester) async {
    await _pump(
      tester,
      repository: FakeGalleryRepository(
        homeFeed: const HomeFeedData(latest: [_design], featured: [], trending: []),
      ),
    );

    expect(find.text('Latest'), findsOneWidget);
    expect(find.text('Bridal Special'), findsOneWidget);
  });

  testWidgets('shows a retry-capable error state when the home feed fails', (tester) async {
    await _pump(
      tester,
      repository: FakeGalleryRepository(homeFeedError: GalleryException('Server unavailable.')),
    );

    expect(find.text('Server unavailable.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('switches to a paginated category view when a chip is tapped', (tester) async {
    await _pump(
      tester,
      repository: FakeGalleryRepository(
        categories: const [_category],
        publishedDesigns: const DesignListData(
          items: [_design],
          pageInfo: PageInfoData(nextCursor: null, hasMore: false),
        ),
      ),
    );

    await tester.tap(find.text('Bridal'));
    await tester.pumpAndSettle();

    expect(find.text('Bridal Special'), findsOneWidget);
    expect(find.text('Latest'), findsNothing);
  });

  testWidgets('shows a Load more button when another page is available', (tester) async {
    final repository = FakeGalleryRepository(
      categories: const [_category],
      publishedDesigns: const DesignListData(
        items: [_design],
        pageInfo: PageInfoData(nextCursor: 'cursor-1', hasMore: true),
      ),
    );
    await _pump(tester, repository: repository);

    await tester.tap(find.text('All Designs'));
    await tester.pumpAndSettle();

    expect(find.text('Load more'), findsOneWidget);
  });
}
