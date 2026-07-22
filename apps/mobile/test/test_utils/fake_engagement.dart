import 'package:mobile/features/engagement/engagement_models.dart';
import 'package:mobile/features/engagement/engagement_repository.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

/// In-memory stand-in for [EngagementRepository] — mirrors
/// test_utils/fake_gallery.dart's approach.
class FakeEngagementRepository implements EngagementRepository {
  FakeEngagementRepository({
    this.likeResult = const LikeStatusData(liked: true, likeCount: 1),
    this.unlikeResult = const LikeStatusData(liked: false, likeCount: 0),
    this.saveResult = const SaveStatusData(saved: true, saveCount: 1),
    this.unsaveResult = const SaveStatusData(saved: false, saveCount: 0),
    DesignListData? savedDesigns,
    this.likeError,
    this.saveError,
  }) : savedDesigns =
           savedDesigns ??
           const DesignListData(
             items: [],
             pageInfo: PageInfoData(nextCursor: null, hasMore: false),
           );

  LikeStatusData likeResult;
  LikeStatusData unlikeResult;
  SaveStatusData saveResult;
  SaveStatusData unsaveResult;
  DesignListData savedDesigns;
  GalleryException? likeError;
  GalleryException? saveError;
  final List<String> likedIds = [];
  final List<String> savedIds = [];

  @override
  Future<LikeStatusData> like(String designId) async {
    if (likeError != null) throw likeError!;
    likedIds.add(designId);
    return likeResult;
  }

  @override
  Future<LikeStatusData> unlike(String designId) async {
    if (likeError != null) throw likeError!;
    return unlikeResult;
  }

  @override
  Future<SaveStatusData> save(String designId) async {
    if (saveError != null) throw saveError!;
    savedIds.add(designId);
    return saveResult;
  }

  @override
  Future<SaveStatusData> unsave(String designId) async {
    if (saveError != null) throw saveError!;
    return unsaveResult;
  }

  @override
  Future<DesignListData> fetchSavedDesigns({String? cursor, int limit = 20}) async =>
      savedDesigns;
}
