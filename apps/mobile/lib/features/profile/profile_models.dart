class ProfileData {
  const ProfileData({
    required this.userId,
    required this.displayName,
    this.avatarUrl,
    this.bio,
    this.city,
    this.country,
    this.locale,
    this.timezone,
  });

  final String userId;
  final String displayName;
  final String? avatarUrl;
  final String? bio;
  final String? city;
  final String? country;
  final String? locale;
  final String? timezone;

  factory ProfileData.fromJson(Map<String, dynamic> json) {
    return ProfileData(
      userId: json['user_id'] as String,
      displayName: json['display_name'] as String,
      avatarUrl: json['avatar_url'] as String?,
      bio: json['bio'] as String?,
      city: json['city'] as String?,
      country: json['country'] as String?,
      locale: json['locale'] as String?,
      timezone: json['timezone'] as String?,
    );
  }
}

/// Mirrors the backend's `UserPreferencesOut` (see
/// app/schemas/profile.py) — notification, marketing, and privacy settings
/// live on one resource, per docs/profile-and-privacy.md.
class PreferencesData {
  const PreferencesData({
    required this.emailNotifications,
    required this.pushNotifications,
    required this.smsNotifications,
    required this.marketingOptIn,
    required this.profileVisibility,
    required this.showLocation,
    required this.allowMessagesFromStrangers,
  });

  final bool emailNotifications;
  final bool pushNotifications;
  final bool smsNotifications;
  final bool marketingOptIn;
  final String profileVisibility;
  final bool showLocation;
  final bool allowMessagesFromStrangers;

  bool get isPrivate => profileVisibility == 'private';

  factory PreferencesData.fromJson(Map<String, dynamic> json) {
    return PreferencesData(
      emailNotifications: json['email_notifications'] as bool,
      pushNotifications: json['push_notifications'] as bool,
      smsNotifications: json['sms_notifications'] as bool,
      marketingOptIn: json['marketing_opt_in'] as bool,
      profileVisibility: json['profile_visibility'] as String,
      showLocation: json['show_location'] as bool,
      allowMessagesFromStrangers: json['allow_messages_from_strangers'] as bool,
    );
  }
}

class BlockedUser {
  const BlockedUser({required this.userId, this.displayName});

  final String userId;
  final String? displayName;

  factory BlockedUser.fromJson(Map<String, dynamic> json) {
    return BlockedUser(
      userId: json['user_id'] as String,
      displayName: json['display_name'] as String?,
    );
  }
}
