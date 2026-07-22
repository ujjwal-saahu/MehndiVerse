import 'package:mobile/features/previews/preview_models.dart';
import 'package:mobile/features/previews/preview_repository.dart';

/// In-memory stand-in for [PreviewRepository] — mirrors
/// test_utils/fake_subscription.dart's approach.
class FakePreviewRepository implements PreviewRepository {
  FakePreviewRepository({
    List<PreviewProjectData>? mine,
    this.one,
    this.fetchMineError,
    this.fetchOneError,
    this.created,
  }) : mine = mine ?? [];

  List<PreviewProjectData> mine;
  PreviewProjectData? one;
  PreviewException? fetchMineError;
  PreviewException? fetchOneError;
  PreviewProjectData? created;
  final List<String> deletedIds = [];
  final List<String> sentToBookingIds = [];

  @override
  Future<List<PreviewProjectData>> fetchMine() async {
    if (fetchMineError != null) throw fetchMineError!;
    return mine;
  }

  @override
  Future<PreviewProjectData> fetchOne(String previewId) async {
    if (fetchOneError != null) throw fetchOneError!;
    if (one == null) throw PreviewException('Preview project not found.');
    return one!;
  }

  @override
  Future<PreviewProjectData> create({
    required List<int> photoBytes,
    required String filename,
    String? designId,
    required OverlayTransform transform,
  }) async {
    return created ??
        PreviewProjectData(
          id: 'created-1',
          sourceImageUrl: 'https://example.test/source.jpg',
          status: 'completed',
        );
  }

  @override
  Future<PreviewProjectData> update(
    String previewId, {
    List<int>? photoBytes,
    String? filename,
    String? designId,
    OverlayTransform? transform,
  }) async {
    return one ??
        PreviewProjectData(
          id: previewId,
          sourceImageUrl: 'https://example.test/source.jpg',
          status: 'completed',
        );
  }

  @override
  Future<String> export(String previewId, {required List<int> compositeBytes}) async {
    return 'https://example.test/result.png';
  }

  @override
  Future<SharePreviewData> share(String previewId) async {
    return const SharePreviewData(url: 'https://example.test/share', expiresInSeconds: 3600);
  }

  @override
  Future<void> sendToArtist(String previewId, {required String bookingId}) async {
    sentToBookingIds.add(bookingId);
  }

  @override
  Future<void> delete(String previewId) async {
    deletedIds.add(previewId);
  }
}
