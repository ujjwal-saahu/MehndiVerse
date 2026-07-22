import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/collections/collection_detail_screen.dart';
import 'package:mobile/features/collections/collection_models.dart';
import 'package:mobile/features/gallery/gallery_models.dart';

import '../../test_utils/fake_collections.dart';

const _collection = CollectionData(
  id: 'c1',
  name: 'Bridal Ideas',
  description: null,
  isDefault: false,
  isPrivate: true,
  isOwner: true,
  coverImageUrl: null,
  itemCount: 1,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
);

const _design = DesignSummaryData(
  id: 'd1',
  artistDisplayName: null,
  title: 'Bridal Special',
  isFeatured: false,
  isPremium: false,
  thumbnailUrl: null,
  viewCount: 0,
);

Future<FakeCollectionRepository> _pump(
  WidgetTester tester, {
  FakeCollectionRepository? repository,
}) async {
  final repo =
      repository ??
      FakeCollectionRepository(
        collection: _collection,
        items: const CollectionItemsData(
          items: [_design],
          pageInfo: PageInfoData(nextCursor: null, hasMore: false),
        ),
      );
  await tester.pumpWidget(
    ProviderScope(
      overrides: [collectionRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: CollectionDetailScreen(collectionId: 'c1')),
    ),
  );
  await tester.pumpAndSettle();
  return repo;
}

void main() {
  testWidgets('shows the collection name and its items', (tester) async {
    await _pump(tester);

    expect(find.text('Bridal Ideas'), findsOneWidget);
    expect(find.text('Bridal Special'), findsOneWidget);
  });

  testWidgets('shows an empty state with no items', (tester) async {
    await _pump(
      tester,
      repository: FakeCollectionRepository(
        collection: _collection,
        items: const CollectionItemsData(
          items: [],
          pageInfo: PageInfoData(nextCursor: null, hasMore: false),
        ),
      ),
    );

    expect(find.text('No designs yet'), findsOneWidget);
  });

  testWidgets('removes an item from the collection', (tester) async {
    final repo = await _pump(tester);

    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();

    expect(find.text('Bridal Special'), findsNothing);
    expect(repo.removedDesignIds, ['d1']);
  });
}
