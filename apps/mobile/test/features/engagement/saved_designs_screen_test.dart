import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/engagement/saved_designs_screen.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

import '../../test_utils/fake_engagement.dart';

const _design = DesignSummaryData(
  id: 'd1',
  artistDisplayName: 'Asha',
  title: 'Bridal Special',
  isFeatured: false,
  isPremium: false,
  thumbnailUrl: null,
  viewCount: 3,
);

Future<void> _pump(WidgetTester tester, {FakeEngagementRepository? repository}) async {
  final repo = repository ?? FakeEngagementRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [engagementRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: SavedDesignsScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows an empty state when nothing is saved', (tester) async {
    await _pump(tester);

    expect(find.text('No saved designs yet'), findsOneWidget);
  });

  testWidgets('shows saved designs once loaded', (tester) async {
    await _pump(
      tester,
      repository: FakeEngagementRepository(
        savedDesigns: const DesignListData(
          items: [_design],
          pageInfo: PageInfoData(nextCursor: null, hasMore: false),
        ),
      ),
    );

    expect(find.text('Bridal Special'), findsOneWidget);
  });

  testWidgets('shows a retry-capable error state when loading fails', (tester) async {
    // FakeEngagementRepository has no error hook for fetchSavedDesigns, so
    // this test uses a minimal inline fake instead.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          engagementRepositoryProvider.overrideWithValue(_ThrowingEngagementRepository()),
        ],
        child: const MaterialApp(home: SavedDesignsScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Server unavailable.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });
}

class _ThrowingEngagementRepository extends FakeEngagementRepository {
  @override
  Future<DesignListData> fetchSavedDesigns({String? cursor, int limit = 20}) async {
    throw GalleryException('Server unavailable.');
  }
}
