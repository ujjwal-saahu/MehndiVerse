import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/artist/artist_dashboard_screen.dart';
import '../../features/artist/artist_directory_screen.dart';
import '../../features/artist/artist_onboarding_screen.dart';
import '../../features/artist/artist_portfolio_screen.dart';
import '../../features/artist/artist_public_profile_screen.dart';
import '../../features/artist/artist_verification_status_screen.dart';
import '../../features/auth/forgot_password_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/auth/verify_email_notice_screen.dart';
import '../../features/bookings/booking_detail_screen.dart';
import '../../features/bookings/bookings_screen.dart';
import '../../features/bookings/my_bookings_screen.dart';
import '../../features/collections/collection_detail_screen.dart';
import '../../features/collections/collections_screen.dart';
import '../../features/engagement/saved_designs_screen.dart';
import '../../features/gallery/design_detail_screen.dart';
import '../../features/home/home_screen.dart';
import '../../features/messages/conversation_detail_screen.dart';
import '../../features/messages/messages_screen.dart';
import '../../features/previews/preview_studio_screen.dart';
import '../../features/previews/previews_list_screen.dart';
import '../../features/profile/blocked_users_screen.dart';
import '../../features/profile/edit_profile_screen.dart';
import '../../features/profile/language_settings_screen.dart';
import '../../features/profile/notification_preferences_screen.dart';
import '../../features/profile/privacy_settings_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/profile/settings_screen.dart';
import '../../features/search/search_screen.dart';
import '../../features/subscriptions/plans_screen.dart';
import '../../features/subscriptions/subscription_status_screen.dart';
import '../auth/auth_models.dart';
import '../navigation/artist_shell.dart';
import '../navigation/customer_shell.dart';
import '../providers.dart';

const _publicRoutes = {'/login', '/register', '/forgot-password', '/verify-email'};
const _artistRoles = {'artist', 'verified_artist'};
// Onboarding/status/portfolio-management routes are the way a plain customer
// *becomes* an artist and manages their own shop (see
// docs/artist-verification.md, docs/artist-directory.md) — they must stay
// reachable by both roles, so they're exempted from the artist-shell gating
// below even though their path starts with '/artist'.
const _artistOnboardingRoutes = {
  '/artist/onboarding',
  '/artist/verification-status',
};

/// Bridges Riverpod's [authControllerProvider] to GoRouter's imperative
/// `refreshListenable`, so navigation reacts to auth-state changes (e.g. a
/// logout while a protected screen is open) without polling.
class _AuthRouterRefresh extends ChangeNotifier {
  _AuthRouterRefresh(Ref ref) {
    ref.listen<AuthState>(authControllerProvider, (previous, next) => notifyListeners());
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final refreshListenable = _AuthRouterRefresh(ref);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: refreshListenable,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final isPublicRoute = _publicRoutes.contains(state.matchedLocation);

      if (authState is AuthStateAuthenticating) return null;

      if (authState is! AuthStateAuthenticated) {
        return isPublicRoute ? null : '/login';
      }

      if (_artistOnboardingRoutes.contains(state.matchedLocation)) return null;

      // Authenticated: customer/artist accounts each land in their own
      // navigation shell — never let one role browse into the other's tabs.
      // Deliberately NOT a bare `startsWith('/artist')`: that would also
      // match the public, both-roles-reachable '/artists' directory
      // (see docs/artist-directory.md) and wrongly treat it as
      // artist-shell-only.
      final isArtist = _artistRoles.contains(authState.user.role);
      final isUnderArtistShell =
          state.matchedLocation == '/artist' || state.matchedLocation.startsWith('/artist/');

      if (isPublicRoute) return isArtist ? '/artist' : '/';
      if (isArtist && !isUnderArtistShell) return '/artist';
      if (!isArtist && isUnderArtistShell) return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/register', builder: (context, state) => const RegisterScreen()),
      GoRoute(
        path: '/forgot-password',
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: '/verify-email',
        builder: (context, state) => VerifyEmailNoticeScreen(email: state.extra as String? ?? ''),
      ),
      // Profile/settings screens are reachable from both the customer and
      // artist shells (see profile_screen.dart) but are not tabs themselves,
      // so they live as ordinary routes pushed on top of whichever shell is
      // active rather than as StatefulShellBranches.
      GoRoute(path: '/profile/edit', builder: (context, state) => const EditProfileScreen()),
      GoRoute(path: '/settings', builder: (context, state) => const SettingsScreen()),
      GoRoute(
        path: '/settings/language',
        builder: (context, state) => const LanguageSettingsScreen(),
      ),
      GoRoute(
        path: '/settings/notifications',
        builder: (context, state) => const NotificationPreferencesScreen(),
      ),
      GoRoute(
        path: '/settings/privacy',
        builder: (context, state) => const PrivacySettingsScreen(),
      ),
      GoRoute(
        path: '/settings/blocked-users',
        builder: (context, state) => const BlockedUsersScreen(),
      ),
      // Hand/foot design preview — see docs/hand-foot-preview.md.
      GoRoute(path: '/previews', builder: (context, state) => const PreviewsListScreen()),
      GoRoute(
        path: '/previews/new',
        builder: (context, state) => const PreviewStudioScreen(),
      ),
      GoRoute(
        path: '/previews/:id',
        builder: (context, state) =>
            PreviewStudioScreen(previewId: state.pathParameters['id']),
      ),
      // Subscriptions — see docs/subscriptions-and-entitlements.md.
      GoRoute(
        path: '/subscription',
        builder: (context, state) => const SubscriptionStatusScreen(),
      ),
      GoRoute(
        path: '/subscription/plans',
        builder: (context, state) => const PlansScreen(),
      ),
      // Artist onboarding/verification — see docs/artist-verification.md.
      // Reachable from both shells (a customer starts here to become an
      // artist; an artist returns here to check status or resubmit), same
      // "pushed on top of whichever shell is active" treatment as
      // /profile/edit above.
      GoRoute(
        path: '/artist/onboarding',
        builder: (context, state) => const ArtistOnboardingScreen(),
      ),
      GoRoute(
        path: '/artist/verification-status',
        builder: (context, state) => const ArtistVerificationStatusScreen(),
      ),
      // Customer-facing artist directory/profile — see
      // docs/artist-directory.md. Reached via the app-bar icon on the
      // Discover tab, same treatment as /search below.
      GoRoute(path: '/artists', builder: (context, state) => const ArtistDirectoryScreen()),
      GoRoute(
        path: '/artists/:id',
        builder: (context, state) =>
            ArtistPublicProfileScreen(artistId: state.pathParameters['id']!),
      ),
      // Shareable design URL — see docs/design-gallery.md
      // #shareable-design-urls. Pushed on top of whichever shell is active,
      // same pattern as the profile/settings routes above.
      GoRoute(
        path: '/design/:id',
        builder: (context, state) =>
            DesignDetailScreen(designId: state.pathParameters['id']!),
      ),
      // Design search — see docs/design-search.md. A plain pushed route
      // (not a StatefulShellBranch/bottom-nav tab) reached via the search
      // icon on the Discover tab's app bar, same treatment as /design/:id.
      GoRoute(path: '/search', builder: (context, state) => const SearchScreen()),
      // Saved-designs shortcut — see docs/engagement-and-collections.md.
      // Also reachable indirectly via the default "Saved Designs" collection
      // under the Collections tab; this is the quick-access shortcut.
      GoRoute(path: '/saved', builder: (context, state) => const SavedDesignsScreen()),
      // Collection detail — pushed on top of the Collections tab.
      GoRoute(
        path: '/collections/:id',
        builder: (context, state) =>
            CollectionDetailScreen(collectionId: state.pathParameters['id']!),
      ),
      // Booking detail/edit — see docs/booking-lifecycle.md. Pushed on top
      // of whichever shell is active (reached from either the My Bookings
      // tab or a "Request a booking" tap on an artist's public profile).
      GoRoute(
        path: '/bookings/:id',
        builder: (context, state) =>
            BookingDetailScreen(bookingId: state.pathParameters['id']!),
      ),
      // Conversation detail — see docs/booking-messaging.md. Routed by
      // booking id (the backend's conversation endpoints are booking-scoped)
      // rather than conversation id; reached from the Messages tab in
      // either shell.
      GoRoute(
        path: '/messages/:bookingId',
        builder: (context, state) =>
            ConversationDetailScreen(bookingId: state.pathParameters['bookingId']!),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            CustomerShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [GoRoute(path: '/', builder: (context, state) => const HomeScreen())],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/collections',
                builder: (context, state) => const CollectionsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/bookings', builder: (context, state) => const MyBookingsScreen()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/messages', builder: (context, state) => const MessagesScreen()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/profile', builder: (context, state) => const ProfileScreen()),
            ],
          ),
        ],
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            ArtistShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/artist',
                builder: (context, state) => const ArtistDashboardScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/artist/bookings',
                builder: (context, state) => const BookingsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/artist/portfolio',
                builder: (context, state) => const ArtistPortfolioScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/artist/messages',
                builder: (context, state) => const MessagesScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/artist/profile',
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});
