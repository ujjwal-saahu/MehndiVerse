import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/collections/collection_models.dart';
import 'package:mobile/features/collections/collections_screen.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

import '../../test_utils/fake_collections.dart';

const _collection = CollectionData(
  id: 'c1',
  name: 'Bridal Ideas',
  description: null,
  isDefault: false,
  isPrivate: true,
  isOwner: true,
  coverImageUrl: null,
  itemCount: 3,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
);

Future<FakeCollectionRepository> _pump(
  WidgetTester tester, {
  FakeCollectionRepository? repository,
}) async {
  final repo = repository ?? FakeCollectionRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [collectionRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: CollectionsScreen()),
    ),
  );
  await tester.pumpAndSettle();
  return repo;
}

void main() {
  testWidgets('shows an empty state with no collections', (tester) async {
    await _pump(tester);

    expect(find.text('No collections yet'), findsOneWidget);
  });

  testWidgets('shows the user\'s collections once loaded', (tester) async {
    await _pump(
      tester,
      repository: FakeCollectionRepository(
        collections: const CollectionListData(
          items: [_collection],
          pageInfo: PageInfoData(nextCursor: null, hasMore: false),
        ),
      ),
    );

    expect(find.text('Bridal Ideas'), findsOneWidget);
    expect(find.text('3 · Private'), findsOneWidget);
  });

  testWidgets('shows a retry-capable error state when loading fails', (tester) async {
    await _pump(
      tester,
      repository: FakeCollectionRepository(fetchError: GalleryException('Server unavailable.')),
    );

    expect(find.text('Server unavailable.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('creates a new collection via the dialog', (tester) async {
    final repo = FakeCollectionRepository(collection: _collection);
    await _pump(tester, repository: repo);

    await tester.tap(find.byIcon(Icons.add));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Bridal Ideas');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();

    expect(repo.createdNames, ['Bridal Ideas']);
  });
}
