import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';
import 'package:mobile/features/search/search_models.dart';
import 'package:mobile/features/search/search_screen.dart';

import '../../test_utils/fake_gallery.dart';
import '../../test_utils/fake_search.dart';

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

Future<FakeSearchRepository> _pump(
  WidgetTester tester, {
  FakeSearchRepository? searchRepository,
  FakeGalleryRepository? galleryRepository,
}) async {
  tester.view.physicalSize = const Size(800, 2000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final searchRepo = searchRepository ?? FakeSearchRepository();
  final galleryRepo = galleryRepository ?? FakeGalleryRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        searchRepositoryProvider.overrideWithValue(searchRepo),
        galleryRepositoryProvider.overrideWithValue(galleryRepo),
      ],
      child: const MaterialApp(home: SearchScreen()),
    ),
  );
  await tester.pumpAndSettle();
  return searchRepo;
}

void main() {
  testWidgets('shows results loaded on open', (tester) async {
    await _pump(
      tester,
      searchRepository: FakeSearchRepository(
        results: const DesignListData(
          items: [_design],
          pageInfo: PageInfoData(nextCursor: null, hasMore: false),
        ),
      ),
    );

    expect(find.text('Bridal Special'), findsOneWidget);
  });

  testWidgets('shows an empty state', (tester) async {
    await _pump(tester);

    expect(find.text('No designs found'), findsOneWidget);
  });

  testWidgets('shows a retry-capable error state when the search fails', (tester) async {
    await _pump(
      tester,
      searchRepository: FakeSearchRepository(searchError: GalleryException('Server unavailable.')),
    );

    expect(find.text('Server unavailable.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('submitting a keyword search re-fetches results', (tester) async {
    final repo = await _pump(tester);

    await tester.enterText(find.byType(TextField), 'peacock');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();

    expect(repo.recordedSearches.last['query'], 'peacock');
  });

  testWidgets('selecting an artist suggestion applies it as a filter chip', (tester) async {
    final repo = await _pump(
      tester,
      searchRepository: FakeSearchRepository(
        suggestions: const [
          SearchSuggestionData(type: 'artist', id: 'a1', label: 'Henna by Asha'),
        ],
      ),
    );

    await tester.enterText(find.byType(TextField), 'asha');
    await tester.pump(const Duration(milliseconds: 350));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Henna by Asha').first);
    await tester.pumpAndSettle();

    expect(find.text('Artist: Henna by Asha'), findsOneWidget);
    expect(repo.recordedSearches.last['artistId'], 'a1');
  });

  testWidgets('shows and clears recent searches', (tester) async {
    final repo = await _pump(
      tester,
      searchRepository: FakeSearchRepository(
        history: const [
          SearchHistoryItemData(id: 'h1', query: 'bridal', createdAt: '2026-01-01T00:00:00Z'),
        ],
      ),
    );

    expect(find.text('bridal'), findsOneWidget);

    await tester.tap(find.text('Clear'));
    await tester.pumpAndSettle();

    expect(find.text('bridal'), findsNothing);
    expect(repo.historyCleared, isTrue);
  });

  testWidgets('tapping a recent search re-runs it', (tester) async {
    final repo = await _pump(
      tester,
      searchRepository: FakeSearchRepository(
        history: const [
          SearchHistoryItemData(id: 'h1', query: 'mandala', createdAt: '2026-01-01T00:00:00Z'),
        ],
      ),
    );

    await tester.tap(find.text('mandala'));
    await tester.pumpAndSettle();

    expect(repo.recordedSearches.last['query'], 'mandala');
  });

  testWidgets('toggling a category filter re-runs the search', (tester) async {
    final repo = await _pump(
      tester,
      galleryRepository: FakeGalleryRepository(categories: const [_category]),
    );

    await tester.tap(find.byIcon(Icons.tune_outlined));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Bridal'));
    await tester.pumpAndSettle();

    expect(repo.recordedSearches.last['categoryIds'], ['c1']);
  });

  testWidgets('shows a Load more button and appends the next page', (tester) async {
    await _pump(
      tester,
      searchRepository: FakeSearchRepository(
        results: const DesignListData(
          items: [_design],
          pageInfo: PageInfoData(nextCursor: 'cursor-1', hasMore: true),
        ),
      ),
    );

    expect(find.text('Load more'), findsOneWidget);
  });
}
