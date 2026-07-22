/// Mirrors the backend's collections schemas (see app/schemas/engagement.py).
library;

import '../gallery/gallery_models.dart';

class CollectionData {
  const CollectionData({
    required this.id,
    required this.name,
    this.description,
    required this.isDefault,
    required this.isPrivate,
    required this.isOwner,
    this.coverImageUrl,
    required this.itemCount,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String name;
  final String? description;
  final bool isDefault;
  final bool isPrivate;
  final bool isOwner;
  final String? coverImageUrl;
  final int itemCount;
  final String createdAt;
  final String updatedAt;

  factory CollectionData.fromJson(Map<String, dynamic> json) {
    return CollectionData(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      isDefault: json['is_default'] as bool,
      isPrivate: json['is_private'] as bool,
      isOwner: json['is_owner'] as bool,
      coverImageUrl: json['cover_image_url'] as String?,
      itemCount: json['item_count'] as int,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );
  }
}

class CollectionListData {
  const CollectionListData({required this.items, required this.pageInfo});

  final List<CollectionData> items;
  final PageInfoData pageInfo;

  factory CollectionListData.fromJson(Map<String, dynamic> json) {
    return CollectionListData(
      items: (json['items'] as List<dynamic>)
          .map((entry) => CollectionData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      pageInfo: PageInfoData.fromJson(json['page_info'] as Map<String, dynamic>),
    );
  }
}

class CollectionItemsData {
  const CollectionItemsData({required this.items, required this.pageInfo});

  final List<DesignSummaryData> items;
  final PageInfoData pageInfo;

  factory CollectionItemsData.fromJson(Map<String, dynamic> json) {
    return CollectionItemsData(
      items: (json['items'] as List<dynamic>)
          .map((entry) => DesignSummaryData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      pageInfo: PageInfoData.fromJson(json['page_info'] as Map<String, dynamic>),
    );
  }
}
