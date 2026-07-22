import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../collections/collection_widgets.dart';
import '../community/community_widgets.dart';
import '../engagement/engagement_widgets.dart';
import 'gallery_models.dart';
import 'gallery_repository.dart';
import 'gallery_widgets.dart';

/// The shareable design-detail screen (`/design/:id`) — see
/// docs/design-gallery.md#shareable-design-urls.
class DesignDetailScreen extends ConsumerStatefulWidget {
  const DesignDetailScreen({required this.designId, super.key});

  final String designId;

  @override
  ConsumerState<DesignDetailScreen> createState() => _DesignDetailScreenState();
}

class _DesignDetailScreenState extends ConsumerState<DesignDetailScreen> {
  Future<DesignDetailData>? _future;
  List<DesignSummaryData> _related = [];
  bool _isDownloading = false;
  String? _downloadError;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final repository = ref.read(galleryRepositoryProvider);
    final future = repository.fetchDesign(widget.designId);
    // Fire-and-forget side effect on success only. Chained off a *copy* of
    // the future reference (not `_future` itself) with its own error
    // handler, so a failed load doesn't produce an unhandled-rejection on
    // top of the one FutureBuilder already surfaces via `_future`.
    future.then((_) => repository.recordView(widget.designId)).catchError((_) {});
    setState(() {
      _future = future;
    });
    repository
        .fetchRelatedDesigns(widget.designId)
        .then((items) {
          if (mounted) setState(() => _related = items);
        })
        .catchError((Object _) {
          // Related designs are a progressive enhancement — fail silently
          // rather than blocking the whole screen on them.
        });
  }

  // Enforced on the backend (premium access + monthly quota) — see
  // docs/subscriptions-and-entitlements.md#download-limits. No
  // file-saving/share package exists in this app yet, so the full-
  // resolution URL is surfaced in a dialog rather than assuming a save-to-
  // gallery flow this codebase hasn't built.
  Future<void> _download(String designId) async {
    setState(() {
      _isDownloading = true;
      _downloadError = null;
    });
    try {
      final imageUrl = await ref.read(galleryRepositoryProvider).downloadDesign(designId);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Full-resolution image'),
          content: SelectableText(imageUrl),
          actions: [
            TextButton(onPressed: () => context.pop(), child: const Text('Close')),
          ],
        ),
      );
    } on GalleryException catch (e) {
      setState(() => _downloadError = e.message);
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Design')),
      body: FutureBuilder<DesignDetailData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading design…');
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return AppErrorState(
              message: error is GalleryException ? error.message : 'Could not load this design.',
              onRetry: _load,
            );
          }

          final design = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(Spacing.s4),
            children: [
              DesignImageGallery(images: design.readyImages, title: design.title),
              const SizedBox(height: Spacing.s4),
              Text(design.title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: Spacing.s1),
              Wrap(
                spacing: Spacing.s2,
                children: [
                  if (design.difficultyLevel != null)
                    Text(design.difficultyLevel!, style: Theme.of(context).textTheme.bodySmall),
                  if (design.bodyPlacement != null)
                    Text('· ${design.bodyPlacement}', style: Theme.of(context).textTheme.bodySmall),
                  if (design.isPremium)
                    Text('· Premium', style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
              if (design.premiumLocked) ...[
                const SizedBox(height: Spacing.s2),
                Container(
                  padding: const EdgeInsets.all(Spacing.s3),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(Radii.md),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          'This is a premium design. Upgrade to a premium plan to see the '
                          'full-resolution images.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.push('/subscription/plans'),
                        child: const Text('Upgrade'),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: Spacing.s3),
              LikeSaveButtons(
                designId: design.id,
                initialIsLiked: design.isLiked,
                initialLikeCount: design.likeCount,
                initialIsSaved: design.isSaved,
                initialSaveCount: design.saveCount,
              ),
              const SizedBox(height: Spacing.s2),
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  AppSecondaryButton(
                    label: 'Add to collection',
                    onPressed: () => showAddToCollectionSheet(context, design.id),
                  ),
                  if (!design.premiumLocked)
                    AppSecondaryButton(
                      label: 'Download',
                      isLoading: _isDownloading,
                      onPressed: () => _download(design.id),
                    ),
                  ReportAction(
                    dialogTitle: 'Report design',
                    label: 'Report design',
                    onReport: (reason) => ref
                        .read(communityRepositoryProvider)
                        .reportDesign(design.id, reason: reason),
                  ),
                ],
              ),
              if (_downloadError != null) ...[
                const SizedBox(height: Spacing.s2),
                Text(
                  _downloadError!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              if (design.description != null) ...[
                const SizedBox(height: Spacing.s3),
                Text(design.description!),
              ],
              if (design.categories.isNotEmpty) ...[
                const SizedBox(height: Spacing.s3),
                Wrap(
                  spacing: Spacing.s2,
                  runSpacing: Spacing.s2,
                  children: design.categories
                      .map((category) => Chip(label: Text(category.name)))
                      .toList(),
                ),
              ],
              if (design.artist != null) ...[
                const SizedBox(height: Spacing.s4),
                ArtistSummaryTile(artist: design.artist!),
              ],
              if (_related.isNotEmpty) ...[
                const SizedBox(height: Spacing.s6),
                Text('Related designs', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: Spacing.s3),
                SizedBox(
                  height: 220,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: _related.length,
                    separatorBuilder: (context, index) => const SizedBox(width: Spacing.s3),
                    itemBuilder: (context, index) => SizedBox(
                      width: 160,
                      child: DesignThumbnailCard(design: _related[index]),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: Spacing.s6),
              CommentsSection(designId: design.id),
            ],
          );
        },
      ),
    );
  }
}
