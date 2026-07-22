import 'package:mobile/features/collections/collection_models.dart';
import 'package:mobile/features/collections/collection_repository.dart';
import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';

/// In-memory stand-in for [CollectionRepository] — mirrors
/// test_utils/fake_gallery.dart's approach.
class FakeCollectionRepository implements CollectionRepository {
  FakeCollectionRepository({
    CollectionListData? collections,
    this.collection,
    CollectionItemsData? items,
    this.fetchError,
  }) : collections =
           collections ??
           const CollectionListData(
             items: [],
             pageInfo: PageInfoData(nextCursor: null, hasMore: false),
           ),
       items =
           items ??
           const CollectionItemsData(
             items: [],
             pageInfo: PageInfoData(nextCursor: null, hasMore: false),
           );

  CollectionListData collections;
  CollectionData? collection;
  CollectionItemsData items;
  GalleryException? fetchError;
  final List<String> createdNames = [];
  final List<String> removedDesignIds = [];
  final List<List<String>> reorderCalls = [];

  @override
  Future<CollectionListData> fetchMyCollections({String? cursor, int limit = 20}) async {
    if (fetchError != null) throw fetchError!;
    return collections;
  }

  @override
  Future<CollectionData> createCollection({
    required String name,
    String? description,
    bool isPrivate = true,
  }) async {
    createdNames.add(name);
    return collection!;
  }

  @override
  Future<CollectionData> fetchCollection(String collectionId) async {
    if (fetchError != null) throw fetchError!;
    return collection!;
  }

  @override
  Future<CollectionData> updateCollection(
    String collectionId, {
    String? name,
    String? description,
    bool? isPrivate,
    String? coverDesignId,
  }) async {
    final current = collection!;
    collection = CollectionData(
      id: current.id,
      name: name ?? current.name,
      description: description ?? current.description,
      isDefault: current.isDefault,
      isPrivate: isPrivate ?? current.isPrivate,
      isOwner: current.isOwner,
      coverImageUrl: current.coverImageUrl,
      itemCount: current.itemCount,
      createdAt: current.createdAt,
      updatedAt: current.updatedAt,
    );
    return collection!;
  }

  @override
  Future<void> deleteCollection(String collectionId) async {}

  @override
  Future<CollectionItemsData> fetchItems(
    String collectionId, {
    String? cursor,
    int limit = 100,
  }) async => items;

  @override
  Future<CollectionItemsData> addItem(String collectionId, String designId) async => items;

  @override
  Future<void> removeItem(String collectionId, String designId) async {
    removedDesignIds.add(designId);
  }

  @override
  Future<CollectionItemsData> reorderItems(String collectionId, List<String> designIds) async {
    reorderCalls.add(designIds);
    return items;
  }
}
