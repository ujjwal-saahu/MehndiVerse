import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/gallery/design_detail_screen.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

import '../../test_utils/fake_gallery.dart';

const _artist = ArtistSummaryData(
  id: 'a1',
  displayName: 'Henna by Asha',
  ratingAverage: 4.8,
  ratingCount: 12,
  isAcceptingBookings: true,
);

const _design = DesignDetailData(
  id: 'd1',
  artist: _artist,
  title: 'Bridal Special',
  description: 'An elaborate bridal design.',
  isPremium: false,
  premiumLocked: false,
  viewCount: 3,
  likeCount: 0,
  saveCount: 0,
  isLiked: false,
  isSaved: false,
  categories: [CategoryData(id: 'c1', name: 'Bridal', slug: 'bridal', categoryType: 'occasion')],
  tags: ['wedding'],
  images: [],
);

Future<FakeGalleryRepository> _pump(
  WidgetTester tester, {
  FakeGalleryRepository? repository,
}) async {
  // The detail screen's content is taller than the default test surface, and
  // ListView only builds children within the viewport + cache extent — grow
  // the surface so every section is actually built and findable, rather
  // than scrolling to each assertion individually.
  tester.view.physicalSize = const Size(800, 3000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final repo = repository ?? FakeGalleryRepository(design: _design);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [galleryRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: DesignDetailScreen(designId: 'd1')),
    ),
  );
  await tester.pumpAndSettle();
  return repo;
}

void main() {
  testWidgets('shows the design title, artist, and category once loaded', (tester) async {
    await _pump(tester);

    expect(find.text('Bridal Special'), findsOneWidget);
    expect(find.text('An elaborate bridal design.'), findsOneWidget);
    expect(find.text('Henna by Asha'), findsOneWidget);
    expect(find.text('Bridal'), findsOneWidget);
  });

  testWidgets('records a view once the design loads', (tester) async {
    final repository = await _pump(tester);

    expect(repository.recordedViews, contains('d1'));
  });

  testWidgets('shows a retry-capable error state when the design fails to load', (tester) async {
    await _pump(
      tester,
      repository: FakeGalleryRepository(designError: GalleryException('Design not found.')),
    );

    expect(find.text('Design not found.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('shows related designs when available', (tester) async {
    await _pump(
      tester,
      repository: FakeGalleryRepository(
        design: _design,
        relatedDesigns: const [
          DesignSummaryData(
            id: 'd2',
            title: 'Arabic Floral',
            isFeatured: false,
            isPremium: false,
            viewCount: 1,
          ),
        ],
      ),
    );

    expect(find.text('Related designs'), findsOneWidget);
    expect(find.text('Arabic Floral'), findsOneWidget);
  });
}
