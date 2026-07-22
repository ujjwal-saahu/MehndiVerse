import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_models.dart';
import '../gallery/gallery_repository.dart';
import '../gallery/gallery_widgets.dart';

/// The saved-designs screen — the quick-save shortcut's own view. See
/// docs/engagement-and-collections.md.
class SavedDesignsScreen extends ConsumerStatefulWidget {
  const SavedDesignsScreen({super.key});

  @override
  ConsumerState<SavedDesignsScreen> createState() => _SavedDesignsScreenState();
}

class _SavedDesignsScreenState extends ConsumerState<SavedDesignsScreen> {
  List<DesignSummaryData> _items = [];
  PageInfoData? _pageInfo;
  bool _isLoading = true;
  bool _isLoadingMore = false;
  GalleryException? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({String? cursor}) async {
    setState(() {
      if (cursor == null) {
        _isLoading = true;
        _error = null;
      } else {
        _isLoadingMore = true;
      }
    });

    try {
      final result = await ref
          .read(engagementRepositoryProvider)
          .fetchSavedDesigns(cursor: cursor);
      if (!mounted) return;
      setState(() {
        _items = cursor == null ? result.items : [..._items, ...result.items];
        _pageInfo = result.pageInfo;
        _isLoading = false;
        _isLoadingMore = false;
      });
    } on GalleryException catch (e) {
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
      appBar: AppBar(title: const Text('Saved Designs')),
      body: RefreshIndicator(onRefresh: () => _load(), child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return ListView(
        children: const [
          Padding(
            padding: EdgeInsets.only(top: Spacing.s16),
            child: AppLoadingView(message: 'Loading saved designs…'),
          ),
        ],
      );
    }
    if (_error != null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s10),
            child: AppErrorState(message: _error!.message, onRetry: () => _load()),
          ),
        ],
      );
    }
    if (_items.isEmpty) {
      return ListView(
        children: const [
          Padding(
            padding: EdgeInsets.only(top: Spacing.s10),
            child: AppEmptyState(
              title: 'No saved designs yet',
              message: 'Tap the save icon on a design to add it here.',
              icon: Icons.bookmark_border,
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
          itemCount: _items.length,
          itemBuilder: (context, index) => DesignThumbnailCard(design: _items[index]),
        ),
        if (_pageInfo?.hasMore == true)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s4),
            child: Center(
              child: _isLoadingMore
                  ? const AppLoadingIndicator()
                  : AppSecondaryButton(
                      label: 'Load more',
                      onPressed: () => _load(cursor: _pageInfo!.nextCursor),
                    ),
            ),
          ),
      ],
    );
  }
}
