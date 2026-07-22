/// Mirrors the backend's public design-gallery schemas (see
/// app/schemas/design.py). Plain hand-written classes, not freezed — these
/// are flat DTOs, not state unions, so the extra codegen isn't worth it
/// (same call made for the profile models in Phase 5).
library;

class CategoryData {
  const CategoryData({
    required this.id,
    required this.name,
    required this.slug,
    required this.categoryType,
  });

  final String id;
  final String name;
  final String slug;
  final String categoryType;

  factory CategoryData.fromJson(Map<String, dynamic> json) {
    return CategoryData(
      id: json['id'] as String,
      name: json['name'] as String,
      slug: json['slug'] as String,
      categoryType: json['category_type'] as String,
    );
  }
}

class ArtistSummaryData {
  const ArtistSummaryData({
    required this.id,
    required this.displayName,
    this.avatarUrl,
    this.headline,
    required this.ratingAverage,
    required this.ratingCount,
    required this.isAcceptingBookings,
  });

  final String id;
  final String displayName;
  final String? avatarUrl;
  final String? headline;
  final double ratingAverage;
  final int ratingCount;
  final bool isAcceptingBookings;

  factory ArtistSummaryData.fromJson(Map<String, dynamic> json) {
    return ArtistSummaryData(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      avatarUrl: json['avatar_url'] as String?,
      headline: json['headline'] as String?,
      ratingAverage: (json['rating_average'] as num).toDouble(),
      ratingCount: json['rating_count'] as int,
      isAcceptingBookings: json['is_accepting_bookings'] as bool,
    );
  }
}

class DesignSummaryData {
  const DesignSummaryData({
    required this.id,
    this.artistDisplayName,
    required this.title,
    required this.isFeatured,
    required this.isPremium,
    this.difficultyLevel,
    this.bodyPlacement,
    this.thumbnailUrl,
    required this.viewCount,
    this.likeCount = 0,
    this.saveCount = 0,
  });

  final String id;
  final String? artistDisplayName;
  final String title;
  final bool isFeatured;
  final bool isPremium;
  final String? difficultyLevel;
  final String? bodyPlacement;
  final String? thumbnailUrl;
  final int viewCount;
  final int likeCount;
  final int saveCount;

  factory DesignSummaryData.fromJson(Map<String, dynamic> json) {
    return DesignSummaryData(
      id: json['id'] as String,
      artistDisplayName: json['artist_display_name'] as String?,
      title: json['title'] as String,
      isFeatured: json['is_featured'] as bool,
      isPremium: json['is_premium'] as bool,
      difficultyLevel: json['difficulty_level'] as String?,
      bodyPlacement: json['body_placement'] as String?,
      thumbnailUrl: json['thumbnail_url'] as String?,
      viewCount: json['view_count'] as int,
      likeCount: json['like_count'] as int? ?? 0,
      saveCount: json['save_count'] as int? ?? 0,
    );
  }
}

class DesignImageData {
  const DesignImageData({
    required this.id,
    required this.status,
    this.imageUrl,
    this.thumbnailSmallUrl,
    this.thumbnailMediumUrl,
    required this.isPrimary,
  });

  final String id;
  final String status;
  final String? imageUrl;
  final String? thumbnailSmallUrl;
  final String? thumbnailMediumUrl;
  final bool isPrimary;

  bool get isReady => status == 'ready' && imageUrl != null;

  factory DesignImageData.fromJson(Map<String, dynamic> json) {
    return DesignImageData(
      id: json['id'] as String,
      status: json['status'] as String,
      imageUrl: json['image_url'] as String?,
      thumbnailSmallUrl: json['thumbnail_small_url'] as String?,
      thumbnailMediumUrl: json['thumbnail_medium_url'] as String?,
      isPrimary: json['is_primary'] as bool,
    );
  }
}

class DesignDetailData {
  const DesignDetailData({
    required this.id,
    this.artist,
    required this.title,
    this.description,
    this.difficultyLevel,
    this.bodyPlacement,
    required this.isPremium,
    required this.premiumLocked,
    required this.viewCount,
    required this.likeCount,
    required this.saveCount,
    required this.isLiked,
    required this.isSaved,
    required this.categories,
    required this.tags,
    required this.images,
  });

  final String id;
  final ArtistSummaryData? artist;
  final String title;
  final String? description;
  final String? difficultyLevel;
  final String? bodyPlacement;
  final bool isPremium;
  // True when this is a premium design and the viewer lacks premium access
  // — see docs/subscriptions-and-entitlements.md#premium-design-access.
  final bool premiumLocked;
  final int viewCount;
  final int likeCount;
  final int saveCount;
  final bool isLiked;
  final bool isSaved;
  final List<CategoryData> categories;
  final List<String> tags;
  final List<DesignImageData> images;

  List<DesignImageData> get readyImages => images.where((image) => image.isReady).toList();

  factory DesignDetailData.fromJson(Map<String, dynamic> json) {
    return DesignDetailData(
      id: json['id'] as String,
      artist: json['artist'] == null
          ? null
          : ArtistSummaryData.fromJson(json['artist'] as Map<String, dynamic>),
      title: json['title'] as String,
      description: json['description'] as String?,
      difficultyLevel: json['difficulty_level'] as String?,
      bodyPlacement: json['body_placement'] as String?,
      isPremium: json['is_premium'] as bool,
      premiumLocked: json['premium_locked'] as bool? ?? false,
      viewCount: json['view_count'] as int,
      likeCount: json['like_count'] as int? ?? 0,
      saveCount: json['save_count'] as int? ?? 0,
      isLiked: json['is_liked'] as bool? ?? false,
      isSaved: json['is_saved'] as bool? ?? false,
      categories: (json['categories'] as List<dynamic>)
          .map((entry) => CategoryData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      tags: (json['tags'] as List<dynamic>).map((entry) => entry as String).toList(),
      images: (json['images'] as List<dynamic>)
          .map((entry) => DesignImageData.fromJson(entry as Map<String, dynamic>))
          .toList(),
    );
  }
}

class PageInfoData {
  const PageInfoData({required this.nextCursor, required this.hasMore});

  final String? nextCursor;
  final bool hasMore;

  factory PageInfoData.fromJson(Map<String, dynamic> json) {
    return PageInfoData(
      nextCursor: json['next_cursor'] as String?,
      hasMore: json['has_more'] as bool,
    );
  }
}

class DesignListData {
  const DesignListData({required this.items, required this.pageInfo});

  final List<DesignSummaryData> items;
  final PageInfoData pageInfo;

  factory DesignListData.fromJson(Map<String, dynamic> json) {
    return DesignListData(
      items: (json['items'] as List<dynamic>)
          .map((entry) => DesignSummaryData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      pageInfo: PageInfoData.fromJson(json['page_info'] as Map<String, dynamic>),
    );
  }
}

class HomeFeedData {
  const HomeFeedData({required this.latest, required this.featured, required this.trending});

  final List<DesignSummaryData> latest;
  final List<DesignSummaryData> featured;
  final List<DesignSummaryData> trending;

  factory HomeFeedData.fromJson(Map<String, dynamic> json) {
    List<DesignSummaryData> section(String key) => (json[key] as List<dynamic>)
        .map((entry) => DesignSummaryData.fromJson(entry as Map<String, dynamic>))
        .toList();

    return HomeFeedData(
      latest: section('latest'),
      featured: section('featured'),
      trending: section('trending'),
    );
  }
}
