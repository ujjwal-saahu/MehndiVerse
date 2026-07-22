import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_repository.dart' show GalleryException;
import 'collection_models.dart';

/// "My Collections" — list, create, and open the user's own collections.
/// See docs/engagement-and-collections.md.
class CollectionsScreen extends ConsumerStatefulWidget {
  const CollectionsScreen({super.key});

  @override
  ConsumerState<CollectionsScreen> createState() => _CollectionsScreenState();
}

class _CollectionsScreenState extends ConsumerState<CollectionsScreen> {
  List<CollectionData> _collections = [];
  bool _isLoading = true;
  GalleryException? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final result = await ref.read(collectionRepositoryProvider).fetchMyCollections(limit: 50);
      if (!mounted) return;
      setState(() {
        _collections = result.items;
        _isLoading = false;
      });
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _isLoading = false;
      });
    }
  }

  Future<void> _createCollection() async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New collection'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'Collection name'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (name == null || name.isEmpty) return;

    try {
      await ref.read(collectionRepositoryProvider).createCollection(name: name);
      await _load();
    } on GalleryException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Collections'),
        actions: [
          IconButton(icon: const Icon(Icons.add), onPressed: _createCollection, tooltip: 'New'),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const AppLoadingView(message: 'Loading collections…');
    }
    if (_error != null) {
      return AppErrorState(message: _error!.message, onRetry: _load);
    }
    if (_collections.isEmpty) {
      return const AppEmptyState(
        title: 'No collections yet',
        message: 'Create a collection to start organizing designs.',
        icon: Icons.collections_bookmark_outlined,
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: GridView.builder(
        padding: const EdgeInsets.all(Spacing.s4),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: Spacing.s3,
          crossAxisSpacing: Spacing.s3,
          childAspectRatio: 0.85,
        ),
        itemCount: _collections.length,
        itemBuilder: (context, index) => _CollectionTile(collection: _collections[index]),
      ),
    );
  }
}

class _CollectionTile extends StatelessWidget {
  const _CollectionTile({required this.collection});

  final CollectionData collection;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: () => context.push('/collections/${collection.id}'),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(Radii.lg),
        child: AspectRatio(
          aspectRatio: 3 / 4,
          child: Stack(
            fit: StackFit.expand,
            children: [
              if (collection.coverImageUrl != null)
                Image.network(collection.coverImageUrl!, fit: BoxFit.cover)
              else
                ColoredBox(
                  color: colors.surfaceContainerHighest,
                  child: const Center(child: Icon(Icons.collections_bookmark_outlined)),
                ),
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.all(Spacing.s2),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Colors.transparent, Colors.black.withValues(alpha: 0.7)],
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        collection.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: FontSizes.sm,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '${collection.itemCount} · ${collection.isPrivate ? 'Private' : 'Public'}',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.8),
                          fontSize: FontSizes.xs,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
