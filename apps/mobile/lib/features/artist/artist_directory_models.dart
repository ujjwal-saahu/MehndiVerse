import '../gallery/gallery_models.dart';

/// Mirrors the backend's `ArtistDirectoryItemOut`/`ArtistPublicProfileOut`/
/// `ArtistServiceOut` (see app/schemas/artist_directory.py) and the web
/// app's src/lib/artist-directory-types.ts.
class ArtistDirectoryItemData {
  const ArtistDirectoryItemData({
    required this.id,
    required this.displayName,
    this.headline,
    this.avatarUrl,
    this.city,
    this.country,
    this.yearsExperience,
    required this.isVerified,
    required this.ratingAverage,
    required this.ratingCount,
    required this.isAcceptingBookings,
  });

  final String id;
  final String displayName;
  final String? headline;
  final String? avatarUrl;
  final String? city;
  final String? country;
  final int? yearsExperience;
  final bool isVerified;
  final double ratingAverage;
  final int ratingCount;
  final bool isAcceptingBookings;

  factory ArtistDirectoryItemData.fromJson(Map<String, dynamic> json) {
    return ArtistDirectoryItemData(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      headline: json['headline'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      city: json['city'] as String?,
      country: json['country'] as String?,
      yearsExperience: json['years_experience'] as int?,
      isVerified: json['is_verified'] as bool,
      ratingAverage: (json['rating_average'] as num).toDouble(),
      ratingCount: json['rating_count'] as int,
      isAcceptingBookings: json['is_accepting_bookings'] as bool,
    );
  }
}

class ArtistDirectoryPageData {
  const ArtistDirectoryPageData({required this.items, required this.pageInfo});

  final List<ArtistDirectoryItemData> items;
  final PageInfoData pageInfo;

  factory ArtistDirectoryPageData.fromJson(Map<String, dynamic> json) {
    return ArtistDirectoryPageData(
      items: (json['items'] as List<dynamic>)
          .map((entry) => ArtistDirectoryItemData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      pageInfo: PageInfoData.fromJson(json['page_info'] as Map<String, dynamic>),
    );
  }
}

class ArtistServiceData {
  const ArtistServiceData({
    required this.id,
    required this.name,
    this.description,
    required this.pricingType,
    this.priceAmount,
    this.priceMin,
    this.priceMax,
    required this.currency,
    this.durationMinutes,
    this.customerCapacity,
    required this.depositRequired,
    this.depositAmount,
    this.travelChargeAmount,
    this.cancellationPolicy,
    required this.isActive,
  });

  final String id;
  final String name;
  final String? description;
  final String pricingType;
  final double? priceAmount;
  final double? priceMin;
  final double? priceMax;
  final String currency;
  final int? durationMinutes;
  final int? customerCapacity;
  final bool depositRequired;
  final double? depositAmount;
  final double? travelChargeAmount;
  final String? cancellationPolicy;
  final bool isActive;

  factory ArtistServiceData.fromJson(Map<String, dynamic> json) {
    return ArtistServiceData(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      pricingType: json['pricing_type'] as String,
      priceAmount: (json['price_amount'] as num?)?.toDouble(),
      priceMin: (json['price_min'] as num?)?.toDouble(),
      priceMax: (json['price_max'] as num?)?.toDouble(),
      currency: json['currency'] as String,
      durationMinutes: json['duration_minutes'] as int?,
      customerCapacity: json['customer_capacity'] as int?,
      depositRequired: json['deposit_required'] as bool,
      depositAmount: (json['deposit_amount'] as num?)?.toDouble(),
      travelChargeAmount: (json['travel_charge_amount'] as num?)?.toDouble(),
      cancellationPolicy: json['cancellation_policy'] as String?,
      isActive: json['is_active'] as bool,
    );
  }
}

class ArtistAvailabilitySlotData {
  const ArtistAvailabilitySlotData({
    required this.dayOfWeek,
    required this.startTime,
    required this.endTime,
  });

  final int dayOfWeek;
  final String startTime;
  final String endTime;

  factory ArtistAvailabilitySlotData.fromJson(Map<String, dynamic> json) {
    return ArtistAvailabilitySlotData(
      dayOfWeek: json['day_of_week'] as int,
      startTime: json['start_time'] as String,
      endTime: json['end_time'] as String,
    );
  }
}

class ArtistPublicProfileData {
  const ArtistPublicProfileData({
    required this.id,
    required this.userId,
    required this.displayName,
    this.headline,
    this.bio,
    this.yearsExperience,
    this.city,
    this.country,
    required this.serviceAreas,
    required this.languages,
    this.profileImageUrl,
    this.coverImageUrl,
    required this.isVerified,
    required this.ratingAverage,
    required this.ratingCount,
    required this.followerCount,
    required this.isFollowed,
    required this.isAcceptingBookings,
    required this.services,
    required this.availabilityPreview,
    required this.portfolioPreview,
    required this.portfolioCount,
  });

  final String id;
  final String userId;
  final String displayName;
  final String? headline;
  final String? bio;
  final int? yearsExperience;
  final String? city;
  final String? country;
  final List<String> serviceAreas;
  final List<String> languages;
  final String? profileImageUrl;
  final String? coverImageUrl;
  final bool isVerified;
  final double ratingAverage;
  final int ratingCount;
  final int followerCount;
  final bool isFollowed;
  final bool isAcceptingBookings;
  final List<ArtistServiceData> services;
  final List<ArtistAvailabilitySlotData> availabilityPreview;
  final List<DesignSummaryData> portfolioPreview;
  final int portfolioCount;

  ArtistPublicProfileData copyWith({bool? isFollowed, int? followerCount}) {
    return ArtistPublicProfileData(
      id: id,
      userId: userId,
      displayName: displayName,
      headline: headline,
      bio: bio,
      yearsExperience: yearsExperience,
      city: city,
      country: country,
      serviceAreas: serviceAreas,
      languages: languages,
      profileImageUrl: profileImageUrl,
      coverImageUrl: coverImageUrl,
      isVerified: isVerified,
      ratingAverage: ratingAverage,
      ratingCount: ratingCount,
      followerCount: followerCount ?? this.followerCount,
      isFollowed: isFollowed ?? this.isFollowed,
      isAcceptingBookings: isAcceptingBookings,
      services: services,
      availabilityPreview: availabilityPreview,
      portfolioPreview: portfolioPreview,
      portfolioCount: portfolioCount,
    );
  }

  factory ArtistPublicProfileData.fromJson(Map<String, dynamic> json) {
    return ArtistPublicProfileData(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      displayName: json['display_name'] as String,
      headline: json['headline'] as String?,
      bio: json['bio'] as String?,
      yearsExperience: json['years_experience'] as int?,
      city: json['city'] as String?,
      country: json['country'] as String?,
      serviceAreas: (json['service_areas'] as List<dynamic>).cast<String>(),
      languages: (json['languages'] as List<dynamic>).cast<String>(),
      profileImageUrl: json['profile_image_url'] as String?,
      coverImageUrl: json['cover_image_url'] as String?,
      isVerified: json['is_verified'] as bool,
      ratingAverage: (json['rating_average'] as num).toDouble(),
      ratingCount: json['rating_count'] as int,
      followerCount: json['follower_count'] as int,
      isFollowed: json['is_followed'] as bool,
      isAcceptingBookings: json['is_accepting_bookings'] as bool,
      services: (json['services'] as List<dynamic>)
          .map((entry) => ArtistServiceData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      availabilityPreview: (json['availability_preview'] as List<dynamic>)
          .map((entry) => ArtistAvailabilitySlotData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      portfolioPreview: (json['portfolio_preview'] as List<dynamic>)
          .map((entry) => DesignSummaryData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      portfolioCount: json['portfolio_count'] as int,
    );
  }
}

const dayNames = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
];
