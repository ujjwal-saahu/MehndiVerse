import 'package:mobile/features/profile/profile_models.dart';
import 'package:mobile/features/profile/profile_repository.dart';

/// In-memory stand-in for [ProfileRepository] so profile/settings widget
/// tests never touch a real backend (mirrors test_utils/fake_auth.dart's
/// approach for AuthRepository).
class FakeProfileRepository implements ProfileRepository {
  FakeProfileRepository({
    ProfileData? profile,
    PreferencesData? preferences,
    List<BlockedUser>? blockedUsers,
  }) : profile =
           profile ??
           const ProfileData(userId: 'u1', displayName: 'Demo User', bio: 'Loves henna art'),
       preferences =
           preferences ??
           const PreferencesData(
             emailNotifications: true,
             pushNotifications: true,
             smsNotifications: false,
             marketingOptIn: false,
             profileVisibility: 'public',
             showLocation: true,
             allowMessagesFromStrangers: true,
           ),
       blockedUsers = blockedUsers ?? [];

  ProfileData profile;
  PreferencesData preferences;
  List<BlockedUser> blockedUsers;
  ProfileException? fetchProfileError;

  @override
  Future<ProfileData> fetchProfile() async {
    if (fetchProfileError != null) throw fetchProfileError!;
    return profile;
  }

  @override
  Future<ProfileData> updateProfile({
    String? displayName,
    String? bio,
    String? city,
    String? country,
    String? locale,
    String? timezone,
  }) async {
    profile = ProfileData(
      userId: profile.userId,
      displayName: displayName ?? profile.displayName,
      avatarUrl: profile.avatarUrl,
      bio: bio ?? profile.bio,
      city: city ?? profile.city,
      country: country ?? profile.country,
      locale: locale ?? profile.locale,
      timezone: timezone ?? profile.timezone,
    );
    return profile;
  }

  @override
  Future<String> uploadAvatar({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async {
    profile = ProfileData(
      userId: profile.userId,
      displayName: profile.displayName,
      avatarUrl: 'https://example.test/avatar.png',
      bio: profile.bio,
      city: profile.city,
      country: profile.country,
      locale: profile.locale,
      timezone: profile.timezone,
    );
    return profile.avatarUrl!;
  }

  @override
  Future<PreferencesData> fetchPreferences() async => preferences;

  @override
  Future<PreferencesData> updatePreferences({
    bool? emailNotifications,
    bool? pushNotifications,
    bool? smsNotifications,
    bool? marketingOptIn,
    String? profileVisibility,
    bool? showLocation,
    bool? allowMessagesFromStrangers,
  }) async {
    preferences = PreferencesData(
      emailNotifications: emailNotifications ?? preferences.emailNotifications,
      pushNotifications: pushNotifications ?? preferences.pushNotifications,
      smsNotifications: smsNotifications ?? preferences.smsNotifications,
      marketingOptIn: marketingOptIn ?? preferences.marketingOptIn,
      profileVisibility: profileVisibility ?? preferences.profileVisibility,
      showLocation: showLocation ?? preferences.showLocation,
      allowMessagesFromStrangers:
          allowMessagesFromStrangers ?? preferences.allowMessagesFromStrangers,
    );
    return preferences;
  }

  @override
  Future<List<BlockedUser>> fetchBlockedUsers() async => blockedUsers;

  @override
  Future<void> blockUser(String userId) async {
    blockedUsers = [...blockedUsers, BlockedUser(userId: userId)];
  }

  @override
  Future<void> unblockUser(String userId) async {
    blockedUsers = blockedUsers.where((user) => user.userId != userId).toList();
  }
}
