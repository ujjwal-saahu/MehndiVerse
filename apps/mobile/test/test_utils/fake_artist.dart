import 'package:mobile/features/artist/artist_directory_models.dart';
import 'package:mobile/features/artist/artist_models.dart';
import 'package:mobile/features/artist/artist_repository.dart';
import 'package:mobile/features/artist/artist_scheduling_models.dart';
import 'package:mobile/features/gallery/gallery_models.dart';

/// In-memory stand-in for [ArtistRepository] — mirrors
/// test_utils/fake_collections.dart's approach. Written best-effort: the
/// Flutter SDK is unavailable in this environment (see
/// docs/artist-verification.md), so this file has not been executed via
/// `flutter test` — it documents intended behavior and should be run as the
/// first step once the SDK is available.
class FakeArtistRepository implements ArtistRepository {
  FakeArtistRepository({ArtistProfileData? profile, this.documents = const [], this.fetchError})
    : profile = profile ?? _draftProfile;

  static const _draftProfile = ArtistProfileData(
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

  ArtistProfileData profile;
  List<ArtistDocumentData> documents;
  ArtistException? fetchError;
  final List<Map<String, dynamic>> patchCalls = [];
  bool submitCalled = false;

  @override
  Future<ArtistProfileData> fetchProfile() async {
    if (fetchError != null) throw fetchError!;
    return profile;
  }

  @override
  Future<ArtistProfileData> updateProfile(Map<String, dynamic> patch) async {
    patchCalls.add(patch);
    return profile;
  }

  @override
  Future<ArtistProfileData> submitProfile() async {
    submitCalled = true;
    return profile;
  }

  @override
  Future<String> uploadProfileImage({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async => 'https://example.test/portfolio/profile-image.jpg';

  @override
  Future<String> uploadCoverImage({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async => 'https://example.test/portfolio/cover-image.jpg';

  @override
  Future<List<ArtistDocumentData>> fetchDocuments() async => documents;

  @override
  Future<ArtistDocumentData> uploadDocument({
    required List<int> bytes,
    required String filename,
    required String contentType,
    required String documentType,
  }) async {
    final document = ArtistDocumentData(
      id: 'd${documents.length + 1}',
      documentType: documentType,
      originalFilename: filename,
      contentType: contentType,
      fileSizeBytes: bytes.length,
      status: 'pending',
      rejectionReason: null,
      reviewedAt: null,
      viewUrl: 'https://example.test/signed/$documentType',
    );
    documents = [...documents, document];
    return document;
  }

  ArtistDirectoryPageData directoryPage =
      const ArtistDirectoryPageData(
        items: [],
        pageInfo: PageInfoData(nextCursor: null, hasMore: false),
      );
  ArtistPublicProfileData? publicProfile;
  final List<String> followedArtistIds = [];
  final List<String> unfollowedArtistIds = [];
  AvailableSlotsData availableSlots = const AvailableSlotsData(
    artistProfileId: 'p1',
    serviceId: 's1',
    artistTimezone: 'UTC',
    slots: [],
  );

  @override
  Future<ArtistDirectoryPageData> fetchDirectory({
    String? city,
    String? country,
    String? service,
    double? minRating,
    bool verifiedOnly = true,
    String? cursor,
    int limit = 20,
  }) async => directoryPage;

  @override
  Future<ArtistPublicProfileData> fetchPublicProfile(String artistId) async {
    return publicProfile ??
        ArtistPublicProfileData(
          id: artistId,
          userId: 'u2',
          displayName: 'Fake Artist',
          serviceAreas: const [],
          languages: const [],
          isVerified: true,
          ratingAverage: 0,
          ratingCount: 0,
          followerCount: 0,
          isFollowed: false,
          isAcceptingBookings: true,
          services: const [],
          availabilityPreview: const [],
          portfolioPreview: const [],
          portfolioCount: 0,
        );
  }

  @override
  Future<void> followArtist(String artistId) async {
    followedArtistIds.add(artistId);
  }

  @override
  Future<void> unfollowArtist(String artistId) async {
    unfollowedArtistIds.add(artistId);
  }

  @override
  Future<AvailableSlotsData> fetchAvailableSlots({
    required String artistId,
    required String serviceId,
    required DateTime startDate,
    required DateTime endDate,
  }) async => availableSlots;
}
