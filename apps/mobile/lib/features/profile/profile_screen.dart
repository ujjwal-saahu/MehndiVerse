import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_models.dart';
import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'profile_models.dart';
import 'profile_repository.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  late Future<ProfileData> _profileFuture;

  @override
  void initState() {
    super.initState();
    _profileFuture = ref.read(profileRepositoryProvider).fetchProfile();
  }

  void _reload() {
    setState(() {
      _profileFuture = ref.read(profileRepositoryProvider).fetchProfile();
    });
  }

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showAppConfirmDialog(
      context,
      title: 'Log out',
      message: 'You will need to log in again to access your account.',
      confirmLabel: 'Log out',
    );
    if (confirmed) {
      await ref.read(authControllerProvider.notifier).logout();
    }
  }

  Future<void> _confirmAccountDeletion(BuildContext context, WidgetRef ref) async {
    final confirmed = await showAppConfirmDialog(
      context,
      title: 'Delete account',
      message: 'This will request deletion of your account. You will be logged out. Continue?',
      confirmLabel: 'Delete',
      isDestructive: true,
    );
    if (confirmed) {
      await ref.read(authControllerProvider.notifier).requestAccountDeletion();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final user = authState is AuthStateAuthenticated ? authState.user : null;

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: FutureBuilder<ProfileData>(
        future: _profileFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading your profile…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as ProfileException?)?.message ??
                  'Could not load your profile.',
              onRetry: _reload,
            );
          }

          final profile = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(Spacing.s4),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          radius: IconSizes.xl,
                          backgroundImage: profile.avatarUrl != null
                              ? NetworkImage(profile.avatarUrl!)
                              : null,
                          child: profile.avatarUrl == null
                              ? const Icon(Icons.person, size: IconSizes.lg)
                              : null,
                        ),
                        const SizedBox(width: Spacing.s4),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                profile.displayName,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              if (user != null)
                                Text(user.email, style: Theme.of(context).textTheme.bodySmall),
                            ],
                          ),
                        ),
                      ],
                    ),
                    if (profile.bio != null) ...[
                      const SizedBox(height: Spacing.s3),
                      Text(profile.bio!, style: Theme.of(context).textTheme.bodyMedium),
                    ],
                    if (profile.city != null || profile.country != null) ...[
                      const SizedBox(height: Spacing.s2),
                      Text(
                        [profile.city, profile.country].whereType<String>().join(', '),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: Spacing.s4),
              AppSecondaryButton(
                label: 'Edit profile',
                onPressed: () async {
                  await context.push('/profile/edit');
                  _reload();
                },
              ),
              const SizedBox(height: Spacing.s3),
              AppSecondaryButton(label: 'Settings', onPressed: () => context.push('/settings')),
              if (user?.role == 'customer' || user?.role == 'premium_customer') ...[
                const SizedBox(height: Spacing.s3),
                AppSecondaryButton(
                  label: 'Become an artist',
                  onPressed: () => context.push('/artist/onboarding'),
                ),
              ],
              if (user?.role == 'artist' || user?.role == 'verified_artist') ...[
                const SizedBox(height: Spacing.s3),
                AppSecondaryButton(
                  label: 'Artist verification status',
                  onPressed: () => context.push('/artist/verification-status'),
                ),
              ],
              const SizedBox(height: Spacing.s6),
              AppSecondaryButton(
                label: 'Log out',
                onPressed: () => _confirmLogout(context, ref),
              ),
              const SizedBox(height: Spacing.s3),
              AppTextActionButton(
                label: 'Delete my account',
                onPressed: () => _confirmAccountDeletion(context, ref),
              ),
            ],
          );
        },
      ),
    );
  }
}
