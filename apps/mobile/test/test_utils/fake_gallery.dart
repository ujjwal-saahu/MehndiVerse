import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

/// In-memory stand-in for [GalleryRepository] so gallery widget tests never
/// touch a real backend (mirrors test_utils/fake_profile.dart's approach).
class FakeGalleryRepository implements GalleryRepository {
  FakeGalleryRepository({
    List<CategoryData>? categories,
    HomeFeedData? homeFeed,
    DesignListData? publishedDesigns,
    this.design,
    List<DesignSummaryData>? relatedDesigns,
    this.homeFeedError,
    this.designError,
    this.downloadUrl,
    this.downloadError,
  }) : categories = categories ?? [],
       homeFeed = homeFeed ?? const HomeFeedData(latest: [], featured: [], trending: []),
       publishedDesigns =
           publishedDesigns ??
           const DesignListData(
             items: [],
             pageInfo: PageInfoData(nextCursor: null, hasMore: false),
           ),
       relatedDesigns = relatedDesigns ?? [];

  List<CategoryData> categories;
  HomeFeedData homeFeed;
  DesignListData publishedDesigns;
  DesignDetailData? design;
  List<DesignSummaryData> relatedDesigns;
  GalleryException? homeFeedError;
  GalleryException? designError;
  String? downloadUrl;
  GalleryException? downloadError;
  final List<String> recordedViews = [];
  final List<String> downloadedDesignIds = [];

  @override
  Future<List<CategoryData>> fetchCategories({String? categoryType}) async => categories;

  @override
  Future<HomeFeedData> fetchHomeFeed() async {
    if (homeFeedError != null) throw homeFeedError!;
    return homeFeed;
  }

  @override
  Future<DesignListData> fetchPublishedDesigns({
    String? categoryId,
    String? difficultyLevel,
    String? bodyPlacement,
    String sort = 'latest',
    String? cursor,
    int limit = 20,
  }) async => publishedDesigns;

  @override
  Future<DesignDetailData> fetchDesign(String designId) async {
    if (designError != null) throw designError!;
    if (design == null) throw GalleryException('Design not found.');
    return design!;
  }

  @override
  Future<List<DesignSummaryData>> fetchRelatedDesigns(String designId) async => relatedDesigns;

  @override
  Future<void> recordView(String designId) async {
    recordedViews.add(designId);
  }

  @override
  Future<String> downloadDesign(String designId) async {
    if (downloadError != null) throw downloadError!;
    downloadedDesignIds.add(designId);
    return downloadUrl ?? 'https://example.test/full.jpg';
  }
}
