import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/engagement/engagement_models.dart';
import 'package:mobile/features/engagement/engagement_widgets.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

import '../../test_utils/fake_engagement.dart';

Future<FakeEngagementRepository> _pump(
  WidgetTester tester, {
  FakeEngagementRepository? repository,
}) async {
  final repo = repository ?? FakeEngagementRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [engagementRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(
        home: Scaffold(
          body: LikeSaveButtons(
            designId: 'd1',
            initialIsLiked: false,
            initialLikeCount: 5,
            initialIsSaved: false,
            initialSaveCount: 2,
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return repo;
}

void main() {
  testWidgets('optimistically likes, then confirms with the server response', (tester) async {
    final repo = await _pump(
      tester,
      repository: FakeEngagementRepository(
        likeResult: const LikeStatusData(liked: true, likeCount: 6),
      ),
    );

    await tester.tap(find.text('Like · 5'));
    await tester.pump();

    expect(find.text('Liked · 6'), findsOneWidget);
    expect(repo.likedIds, ['d1']);
  });

  testWidgets('rolls back the optimistic like when the server call fails', (tester) async {
    await _pump(
      tester,
      repository: FakeEngagementRepository(likeError: GalleryException('Server unavailable.')),
    );

    await tester.tap(find.text('Like · 5'));
    await tester.pumpAndSettle();

    expect(find.text('Like · 5'), findsOneWidget);
    expect(find.text('Server unavailable.'), findsOneWidget);
  });

  testWidgets('optimistically saves, then confirms with the server response', (tester) async {
    await _pump(
      tester,
      repository: FakeEngagementRepository(
        saveResult: const SaveStatusData(saved: true, saveCount: 3),
      ),
    );

    await tester.tap(find.text('Save · 2'));
    await tester.pump();

    expect(find.text('Saved · 3'), findsOneWidget);
  });
}
