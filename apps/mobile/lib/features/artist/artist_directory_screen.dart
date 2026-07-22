import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_models.dart';
import 'artist_directory_models.dart';
import 'artist_repository.dart';

/// Customer-facing artist directory — see docs/artist-directory.md. Reached
/// from the Discover tab's app bar, the same "pushed route via an app-bar
/// icon" treatment Phase 8's search screen established.
class ArtistDirectoryScreen extends ConsumerStatefulWidget {
  const ArtistDirectoryScreen({super.key});

  @override
  ConsumerState<ArtistDirectoryScreen> createState() => _ArtistDirectoryScreenState();
}

class _ArtistDirectoryScreenState extends ConsumerState<ArtistDirectoryScreen> {
  final _cityController = TextEditingController();
  final _countryController = TextEditingController();
  final _serviceController = TextEditingController();
  bool _verifiedOnly = true;

  List<ArtistDirectoryItemData> _items = [];
  PageInfoData? _pageInfo;
  bool _isLoading = true;
  bool _isLoadingMore = false;
  ArtistException? _error;

  @override
  void initState() {
    super.initState();
    _search();
  }

  @override
  void dispose() {
    _cityController.dispose();
    _countryController.dispose();
    _serviceController.dispose();
    super.dispose();
  }

  Future<void> _search({String? cursor}) async {
    setState(() {
      if (cursor == null) {
        _isLoading = true;
        _error = null;
      } else {
        _isLoadingMore = true;
      }
    });
    try {
      final page = await ref
          .read(artistRepositoryProvider)
          .fetchDirectory(
            city: _cityController.text.trim().isEmpty ? null : _cityController.text.trim(),
            country: _countryController.text.trim().isEmpty
                ? null
                : _countryController.text.trim(),
            service: _serviceController.text.trim().isEmpty
                ? null
                : _serviceController.text.trim(),
            verifiedOnly: _verifiedOnly,
            cursor: cursor,
          );
      if (!mounted) return;
      setState(() {
        _items = cursor == null ? page.items : [..._items, ...page.items];
        _pageInfo = page.pageInfo;
        _isLoading = false;
        _isLoadingMore = false;
      });
    } on ArtistException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Find an artist')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(Spacing.s4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AppTextField(label: 'City', controller: _cityController),
                const SizedBox(height: Spacing.s2),
                AppTextField(label: 'Country (e.g. IN)', controller: _countryController),
                const SizedBox(height: Spacing.s2),
                AppTextField(label: 'Service', controller: _serviceController),
                const SizedBox(height: Spacing.s2),
                Row(
                  children: [
                    Checkbox(
                      value: _verifiedOnly,
                      onChanged: (value) => setState(() => _verifiedOnly = value ?? true),
                    ),
                    const Text('Verified only'),
                  ],
                ),
                AppPrimaryButton(label: 'Search', onPressed: () => _search()),
              ],
            ),
          ),
          Expanded(child: _buildResults()),
        ],
      ),
    );
  }

  Widget _buildResults() {
    if (_isLoading) {
      return const AppLoadingView(message: 'Loading artists…');
    }
    if (_error != null) {
      return AppErrorState(message: _error!.message, onRetry: () => _search());
    }
    if (_items.isEmpty) {
      return const AppEmptyState(
        title: 'No artists found',
        message: 'Try adjusting your filters.',
        icon: Icons.person_search_outlined,
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(Spacing.s4),
      itemCount: _items.length + (_pageInfo?.hasMore == true ? 1 : 0),
      separatorBuilder: (context, index) => const SizedBox(height: Spacing.s3),
      itemBuilder: (context, index) {
        if (index >= _items.length) {
          return Center(
            child: _isLoadingMore
                ? const AppLoadingIndicator()
                : AppSecondaryButton(
                    label: 'Load more',
                    onPressed: () => _search(cursor: _pageInfo!.nextCursor),
                  ),
          );
        }

        final artist = _items[index];
        return AppCard(
          onTap: () => context.push('/artists/${artist.id}'),
          child: Row(
            children: [
              CircleAvatar(
                radius: IconSizes.lg,
                backgroundImage: artist.avatarUrl != null
                    ? NetworkImage(artist.avatarUrl!)
                    : null,
                child: artist.avatarUrl == null
                    ? const Icon(Icons.person, size: IconSizes.md)
                    : null,
              ),
              const SizedBox(width: Spacing.s3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            artist.displayName,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ),
                        if (artist.isVerified) ...[
                          const SizedBox(width: Spacing.s1),
                          const Icon(Icons.verified, size: IconSizes.xs, color: Colors.blue),
                        ],
                      ],
                    ),
                    if (artist.headline != null)
                      Text(
                        artist.headline!,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    Text(
                      [artist.city, artist.country].whereType<String>().join(', '),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    Text(
                      artist.ratingCount > 0
                          ? '★ ${artist.ratingAverage.toStringAsFixed(1)} (${artist.ratingCount})'
                          : 'No reviews yet',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
