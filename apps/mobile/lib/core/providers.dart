import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/artist/artist_repository.dart';
import '../features/bookings/booking_repository.dart';
import '../features/collections/collection_repository.dart';
import '../features/community/community_repository.dart';
import '../features/engagement/engagement_repository.dart';
import '../features/gallery/gallery_repository.dart';
import '../features/messages/messaging_repository.dart';
import '../features/previews/preview_repository.dart';
import '../features/profile/profile_repository.dart';
import '../features/search/search_repository.dart';
import '../features/subscriptions/subscription_repository.dart';
import 'auth/auth_controller.dart';
import 'auth/auth_models.dart';
import 'auth/auth_repository.dart';
import 'auth/token_storage.dart';
import 'config/app_environment.dart';
import 'network/api_client.dart';

final appEnvironmentProvider = Provider<AppEnvironment>((ref) => AppEnvironment.development());

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

final apiClientProvider = Provider<ApiClient>((ref) {
  final environment = ref.watch(appEnvironmentProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);
  return ApiClient(environment, tokenStorage);
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider).dio);
});

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepository(ref.watch(apiClientProvider).dio);
});

final artistRepositoryProvider = Provider<ArtistRepository>((ref) {
  return ArtistRepository(ref.watch(apiClientProvider).dio);
});

final bookingRepositoryProvider = Provider<BookingRepository>((ref) {
  return BookingRepository(ref.watch(apiClientProvider).dio);
});

final messagingRepositoryProvider = Provider<MessagingRepository>((ref) {
  return MessagingRepository(ref.watch(apiClientProvider).dio);
});

final galleryRepositoryProvider = Provider<GalleryRepository>((ref) {
  return GalleryRepository(ref.watch(apiClientProvider).dio);
});

final searchRepositoryProvider = Provider<SearchRepository>((ref) {
  return SearchRepository(ref.watch(apiClientProvider).dio);
});

final engagementRepositoryProvider = Provider<EngagementRepository>((ref) {
  return EngagementRepository(ref.watch(apiClientProvider).dio);
});

final collectionRepositoryProvider = Provider<CollectionRepository>((ref) {
  return CollectionRepository(ref.watch(apiClientProvider).dio);
});

final communityRepositoryProvider = Provider<CommunityRepository>((ref) {
  return CommunityRepository(ref.watch(apiClientProvider).dio);
});

final subscriptionRepositoryProvider = Provider<SubscriptionRepository>((ref) {
  return SubscriptionRepository(ref.watch(apiClientProvider).dio);
});

final previewRepositoryProvider = Provider<PreviewRepository>((ref) {
  return PreviewRepository(ref.watch(apiClientProvider).dio);
});

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(ref.watch(authRepositoryProvider), ref.watch(tokenStorageProvider));
});
