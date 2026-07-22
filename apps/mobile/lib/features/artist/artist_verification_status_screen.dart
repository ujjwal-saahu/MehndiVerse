import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'artist_models.dart';
import 'artist_repository.dart';

/// Read-only verification-status screen — see
/// docs/artist-verification.md#verification-lifecycle. Mirrors the web
/// app's src/app/(marketing)/artist/verification-status/page.tsx.
class ArtistVerificationStatusScreen extends ConsumerStatefulWidget {
  const ArtistVerificationStatusScreen({super.key});

  @override
  ConsumerState<ArtistVerificationStatusScreen> createState() =>
      _ArtistVerificationStatusScreenState();
}

class _ArtistVerificationStatusScreenState
    extends ConsumerState<ArtistVerificationStatusScreen> {
  late Future<(ArtistProfileData, List<ArtistDocumentData>)> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<(ArtistProfileData, List<ArtistDocumentData>)> _load() async {
    final repository = ref.read(artistRepositoryProvider);
    final profile = await repository.fetchProfile();
    final documents = await repository.fetchDocuments();
    return (profile, documents);
  }

  void _reload() {
    setState(() => _future = _load());
  }

  Color _statusColor(BuildContext context, String status) {
    final scheme = Theme.of(context).colorScheme;
    switch (status) {
      case 'approved':
        return Colors.green;
      case 'rejected':
      case 'suspended':
        return scheme.error;
      case 'more_information_required':
        return Colors.orange;
      default:
        return scheme.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Verification status')),
      body: FutureBuilder<(ArtistProfileData, List<ArtistDocumentData>)>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading verification status…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as ArtistException?)?.message ??
                  'Could not load your verification status.',
              onRetry: _reload,
            );
          }

          final (profile, documents) = snapshot.data!;
          final statusLabel =
              artistVerificationStatusLabels[profile.verificationStatus] ??
              profile.verificationStatus;

          return ListView(
            padding: const EdgeInsets.all(Spacing.s4),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Chip(
                      label: Text(statusLabel),
                      backgroundColor: _statusColor(
                        context,
                        profile.verificationStatus,
                      ).withValues(alpha: 0.15),
                      labelStyle: TextStyle(
                        color: _statusColor(context, profile.verificationStatus),
                      ),
                    ),
                    if (profile.professionalName != null) ...[
                      const SizedBox(height: Spacing.s3),
                      Text(
                        profile.professionalName!,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                    if ((profile.verificationStatus == 'rejected' ||
                            profile.verificationStatus == 'suspended') &&
                        profile.rejectionReason != null) ...[
                      const SizedBox(height: Spacing.s3),
                      Text(
                        'Reason: ${profile.rejectionReason}',
                        style: TextStyle(color: Theme.of(context).colorScheme.error),
                      ),
                    ],
                    if (profile.verificationStatus == 'more_information_required' &&
                        profile.moreInfoRequest != null) ...[
                      const SizedBox(height: Spacing.s3),
                      Text('We need more information: ${profile.moreInfoRequest}'),
                    ],
                    if (profile.isEditable) ...[
                      const SizedBox(height: Spacing.s4),
                      AppPrimaryButton(
                        label: profile.verificationStatus == 'draft'
                            ? 'Continue your application'
                            : 'Update and resubmit',
                        onPressed: () async {
                          await context.push('/artist/onboarding');
                          _reload();
                        },
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: Spacing.s4),
              Text('Documents', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: Spacing.s2),
              if (documents.isEmpty)
                Text(
                  'No documents uploaded yet.',
                  style: Theme.of(context).textTheme.bodyMedium,
                )
              else
                for (final document in documents)
                  AppCard(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(document.originalFilename ?? document.documentType),
                              Text(
                                document.documentType.replaceAll('_', ' '),
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                        ),
                        Text(document.status),
                      ],
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }
}
