import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_models.dart';
import '../gallery/gallery_repository.dart';
import '../gallery/gallery_widgets.dart';

/// The "Discover" tab: home feed (Latest/Featured/Trending) plus
/// category-filtered, paginated browsing — see
/// docs/design-gallery.md#home-feed and #category-browsing.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  List<CategoryData> _categories = [];
  String _activeKey = 'home';

  Future<HomeFeedData>? _homeFeedFuture;

  List<DesignSummaryData> _browseItems = [];
  PageInfoData? _browsePageInfo;
  bool _isBrowseLoading = false;
  bool _isLoadingMore = false;
  GalleryException? _browseError;

  @override
  void initState() {
    super.initState();
    _loadCategories();
    _loadHomeFeed();
  }

  void _loadCategories() {
    ref
        .read(galleryRepositoryProvider)
        .fetchCategories()
        .then((categories) {
          if (mounted) setState(() => _categories = categories);
        })
        .catchError((Object _) {
          // Category chips are a progressive enhancement over the home feed
          // — fail silently rather than blocking the whole screen on them.
        });
  }

  void _loadHomeFeed() {
    setState(() {
      _homeFeedFuture = ref.read(galleryRepositoryProvider).fetchHomeFeed();
    });
  }

  Future<void> _loadBrowse(String? categoryId, {String? cursor}) async {
    setState(() {
      if (cursor == null) {
        _isBrowseLoading = true;
        _browseError = null;
      } else {
        _isLoadingMore = true;
      }
    });

    try {
      final result = await ref
          .read(galleryRepositoryProvider)
          .fetchPublishedDesigns(categoryId: categoryId, cursor: cursor);
      if (!mounted) return;
      setState(() {
        _browseItems = cursor == null ? result.items : [..._browseItems, ...result.items];
        _browsePageInfo = result.pageInfo;
        _isBrowseLoading = false;
        _isLoadingMore = false;
      });
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() {
        _browseError = e;
        _isBrowseLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  void _onSelectChip(String key) {
    setState(() => _activeKey = key);
    if (key == 'home') {
      _loadHomeFeed();
    } else {
      _loadBrowse(key == 'all' ? null : key);
    }
  }

  Future<void> _onRefresh() async {
    if (_activeKey == 'home') {
      _loadHomeFeed();
      await _homeFeedFuture;
    } else {
      await _loadBrowse(_activeKey == 'all' ? null : _activeKey);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Discover'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_search_outlined),
            tooltip: 'Find an artist',
            onPressed: () => context.push('/artists'),
          ),
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Search',
            onPressed: () => context.push('/search'),
          ),
          IconButton(
            icon: const Icon(Icons.bookmark_border),
            tooltip: 'Saved Designs',
            onPressed: () => context.push('/saved'),
          ),
        ],
      ),
      body: Column(
        children: [
          CategoryChipsRow(
            categories: _categories,
            activeKey: _activeKey,
            onSelect: _onSelectChip,
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _onRefresh,
              child: _activeKey == 'home' ? _buildHomeFeed() : _buildBrowse(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHomeFeed() {
    return FutureBuilder<HomeFeedData>(
      future: _homeFeedFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return ListView(
            children: const [
              Padding(
                padding: EdgeInsets.only(top: Spacing.s16),
                child: AppLoadingView(message: 'Loading designs…'),
              ),
            ],
          );
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          return ListView(
            children: [
              Padding(
                padding: const EdgeInsets.only(top: Spacing.s10),
                child: AppErrorState(
                  message: error is GalleryException
                      ? error.message
                      : 'Could not load designs.',
                  onRetry: _loadHomeFeed,
                ),
              ),
            ],
          );
        }

        final feed = snapshot.data!;
        if (feed.latest.isEmpty && feed.featured.isEmpty && feed.trending.isEmpty) {
          return ListView(
            children: const [
              Padding(
                padding: EdgeInsets.only(top: Spacing.s10),
                child: AppEmptyState(
                  title: 'No designs yet',
                  message: 'Check back soon for new mehndi designs.',
                  icon: Icons.auto_awesome_outlined,
                ),
              ),
            ],
          );
        }

        return ListView(
          padding: const EdgeInsets.symmetric(vertical: Spacing.s4),
          children: [
            if (feed.latest.isNotEmpty) DesignSectionRow(title: 'Latest', designs: feed.latest),
            if (feed.featured.isNotEmpty)
              DesignSectionRow(title: 'Featured', designs: feed.featured),
            if (feed.trending.isNotEmpty)
              DesignSectionRow(title: 'Trending', designs: feed.trending),
          ],
        );
      },
    );
  }

  Widget _buildBrowse() {
    if (_isBrowseLoading) {
      return ListView(
        children: const [
          Padding(
            padding: EdgeInsets.only(top: Spacing.s16),
            child: AppLoadingView(message: 'Loading designs…'),
          ),
        ],
      );
    }
    if (_browseError != null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s10),
            child: AppErrorState(
              message: _browseError!.message,
              onRetry: () => _loadBrowse(_activeKey == 'all' ? null : _activeKey),
            ),
          ),
        ],
      );
    }
    if (_browseItems.isEmpty) {
      return ListView(
        children: const [
          Padding(
            padding: EdgeInsets.only(top: Spacing.s10),
            child: AppEmptyState(
              title: 'No designs found',
              message: 'Try a different category.',
              icon: Icons.search_off_outlined,
            ),
          ),
        ],
      );
    }

    return ListView(
      padding: const EdgeInsets.all(Spacing.s4),
      children: [
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            mainAxisSpacing: Spacing.s3,
            crossAxisSpacing: Spacing.s3,
            childAspectRatio: 0.72,
          ),
          itemCount: _browseItems.length,
          itemBuilder: (context, index) => DesignThumbnailCard(design: _browseItems[index]),
        ),
        if (_browsePageInfo?.hasMore == true)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s4),
            child: Center(
              child: _isLoadingMore
                  ? const AppLoadingIndicator()
                  : AppSecondaryButton(
                      label: 'Load more',
                      onPressed: () => _loadBrowse(
                        _activeKey == 'all' ? null : _activeKey,
                        cursor: _browsePageInfo!.nextCursor,
                      ),
                    ),
            ),
          ),
      ],
    );
  }
}
