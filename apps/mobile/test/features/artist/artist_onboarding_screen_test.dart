import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/artist/artist_models.dart';
import 'package:mobile/features/artist/artist_onboarding_screen.dart';
import 'package:mobile/features/artist/artist_repository.dart';

import '../../test_utils/fake_artist.dart';

// Best-effort: the Flutter SDK is unavailable in this environment (see
// docs/artist-verification.md), so this file has not been executed via
// `flutter test`. Run it as the first verification step once the SDK is
// available.

const _draftProfile = ArtistProfileData(
  id: 'p1',
  userId: 'u1',
  professionalName: null,
  businessName: null,
  headline: null,
  bio: null,
  yearsExperience: null,
  country: null,
  city: null,
  serviceAreas: [],
  languages: [],
  contactEmail: null,
  contactPhone: null,
  socialLinks: {},
  profileImageUrl: null,
  coverImageUrl: null,
  verificationStatus: 'draft',
  submittedAt: null,
  reviewedAt: null,
  rejectionReason: null,
  moreInfoRequest: null,
  isEditable: true,
  missingRequirements: ['professional_name', 'bio', 'identity_document'],
);

Future<void> _pump(WidgetTester tester, {required FakeArtistRepository repository}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [artistRepositoryProvider.overrideWithValue(repository)],
      child: const MaterialApp(home: ArtistOnboardingScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows a read-only message instead of the form when not editable', (tester) async {
    final notEditable = ArtistProfileData(
      id: _draftProfile.id,
      userId: _draftProfile.userId,
      professionalName: null,
      businessName: null,
      headline: null,
      bio: null,
      yearsExperience: null,
      country: null,
      city: null,
      serviceAreas: const [],
      languages: const [],
      contactEmail: null,
      contactPhone: null,
      socialLinks: const {},
      profileImageUrl: null,
      coverImageUrl: null,
      verificationStatus: 'submitted',
      submittedAt: null,
      reviewedAt: null,
      rejectionReason: null,
      moreInfoRequest: null,
      isEditable: false,
      missingRequirements: const [],
    );

    await _pump(tester, repository: FakeArtistRepository(profile: notEditable));

    expect(find.textContaining("can't be edited right now"), findsOneWidget);
    expect(find.text('Professional name'), findsNothing);
  });

  testWidgets('saves the current step and advances to the next one', (tester) async {
    final repository = FakeArtistRepository(profile: _draftProfile);
    await _pump(tester, repository: repository);

    await tester.enterText(find.widgetWithText(TextFormField, 'Professional name'), 'Priya');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Country (e.g. IN)'), findsOneWidget);
    expect(repository.patchCalls, hasLength(1));
    expect(repository.patchCalls.first['professional_name'], 'Priya');
  });

  testWidgets('disables submission while requirements are missing on the review step', (
    tester,
  ) async {
    final repository = FakeArtistRepository(profile: _draftProfile);
    await _pump(tester, repository: repository);

    for (var i = 0; i < 3; i++) {
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }
    // Steps 3 (Photos) and 4 (Documents) advance without a network call.
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Before you can submit:'), findsOneWidget);
    final submitButton = tester.widget<ElevatedButton>(
      find.widgetWithText(ElevatedButton, 'Submit for review'),
    );
    expect(submitButton.onPressed, isNull);
  });

  testWidgets('shows a retry-capable error state when loading fails', (tester) async {
    await _pump(
      tester,
      repository: FakeArtistRepository(fetchError: ArtistException('Server unavailable.')),
    );

    expect(find.text('Server unavailable.'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });
}
