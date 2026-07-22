import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/providers.dart';
import 'package:mobile/features/artist/artist_models.dart';
import 'package:mobile/features/artist/artist_repository.dart';
import 'package:mobile/features/artist/artist_verification_status_screen.dart';

import '../../test_utils/fake_artist.dart';

// Best-effort: the Flutter SDK is unavailable in this environment (see
// docs/artist-verification.md), so this file has not been executed via
// `flutter test`. Run it as the first verification step once the SDK is
// available.

const _approvedProfile = ArtistProfileData(
  id: 'p1',
  userId: 'u1',
  professionalName: 'Priya Sharma',
  businessName: null,
  headline: null,
  bio: 'Ten years of bridal henna.',
  yearsExperience: 10,
  country: 'IN',
  city: 'Jaipur',
  serviceAreas: [],
  languages: [],
  contactEmail: null,
  contactPhone: null,
  socialLinks: {},
  profileImageUrl: null,
  coverImageUrl: null,
  verificationStatus: 'approved',
  submittedAt: null,
  reviewedAt: null,
  rejectionReason: null,
  moreInfoRequest: null,
  isEditable: false,
  missingRequirements: [],
);

Future<void> _pump(WidgetTester tester, {required FakeArtistRepository repository}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [artistRepositoryProvider.overrideWithValue(repository)],
      child: const MaterialApp(home: ArtistVerificationStatusScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows the current status label and professional name', (tester) async {
    await _pump(tester, repository: FakeArtistRepository(profile: _approvedProfile));

    expect(find.text('Approved'), findsOneWidget);
    expect(find.text('Priya Sharma'), findsOneWidget);
  });

  testWidgets('shows the rejection reason when rejected', (tester) async {
    final rejected = ArtistProfileData(
      id: _approvedProfile.id,
      userId: _approvedProfile.userId,
      professionalName: _approvedProfile.professionalName,
      businessName: null,
      headline: null,
      bio: _approvedProfile.bio,
      yearsExperience: _approvedProfile.yearsExperience,
      country: _approvedProfile.country,
      city: _approvedProfile.city,
      serviceAreas: const [],
      languages: const [],
      contactEmail: null,
      contactPhone: null,
      socialLinks: const {},
      profileImageUrl: null,
      coverImageUrl: null,
      verificationStatus: 'rejected',
      submittedAt: null,
      reviewedAt: null,
      rejectionReason: 'Photo of ID is blurry.',
      moreInfoRequest: null,
      isEditable: true,
      missingRequirements: const [],
    );

    await _pump(tester, repository: FakeArtistRepository(profile: rejected));

    expect(find.text('Reason: Photo of ID is blurry.'), findsOneWidget);
    expect(find.text('Update and resubmit'), findsOneWidget);
  });

  testWidgets('shows an empty state when no documents are uploaded', (tester) async {
    await _pump(tester, repository: FakeArtistRepository(profile: _approvedProfile));

    expect(find.text('No documents uploaded yet.'), findsOneWidget);
  });

  testWidgets('lists uploaded documents with their status', (tester) async {
    await _pump(
      tester,
      repository: FakeArtistRepository(
        profile: _approvedProfile,
        documents: const [
          ArtistDocumentData(
            id: 'd1',
            documentType: 'id_proof',
            originalFilename: 'id.jpg',
            contentType: 'image/jpeg',
            fileSizeBytes: 1024,
            status: 'approved',
            rejectionReason: null,
            reviewedAt: null,
            viewUrl: 'https://example.test/signed/id.jpg',
          ),
        ],
      ),
    );

    expect(find.text('id.jpg'), findsOneWidget);
    expect(find.text('approved'), findsOneWidget);
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
