import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_models.dart';
import '../gallery/gallery_repository.dart' show GalleryException;
import 'collection_models.dart';

// Fetched in one large page rather than the usual paginated size —
// reordering only makes sense against the collection's *entire* item list
// (the backend rejects a reorder that doesn't name every current item
// exactly once). See docs/engagement-and-collections.md.
const _itemsPageSize = 100;

/// Collection detail — items grid, rename/delete, public/private toggle,
/// remove item, and reorder (owner-only controls). See
/// docs/engagement-and-collections.md.
class CollectionDetailScreen extends ConsumerStatefulWidget {
  const CollectionDetailScreen({required this.collectionId, super.key});

  final String collectionId;

  @override
  ConsumerState<CollectionDetailScreen> createState() => _CollectionDetailScreenState();
}

class _CollectionDetailScreenState extends ConsumerState<CollectionDetailScreen> {
  CollectionData? _collection;
  List<DesignSummaryData> _items = [];
  PageInfoData? _pageInfo;
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
      final repository = ref.read(collectionRepositoryProvider);
      final collection = await repository.fetchCollection(widget.collectionId);
      final items = await repository.fetchItems(widget.collectionId, limit: _itemsPageSize);
      if (!mounted) return;
      setState(() {
        _collection = collection;
        _items = items.items;
        _pageInfo = items.pageInfo;
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

  bool get _canReorder => _pageInfo?.hasMore != true;

  Future<void> _rename() async {
    final controller = TextEditingController(text: _collection!.name);
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename collection'),
        content: TextField(controller: controller, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (name == null || name.isEmpty || name == _collection!.name) return;

    try {
      final updated = await ref
          .read(collectionRepositoryProvider)
          .updateCollection(widget.collectionId, name: name);
      if (mounted) setState(() => _collection = updated);
    } on GalleryException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _togglePrivacy() async {
    try {
      final updated = await ref
          .read(collectionRepositoryProvider)
          .updateCollection(widget.collectionId, isPrivate: !_collection!.isPrivate);
      if (mounted) setState(() => _collection = updated);
    } on GalleryException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this collection?'),
        content: const Text("This can't be undone."),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await ref.read(collectionRepositoryProvider).deleteCollection(widget.collectionId);
      if (mounted) context.pop();
    } on GalleryException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _removeItem(String designId) async {
    final previous = _items;
    setState(() => _items = _items.where((d) => d.id != designId).toList());
    try {
      await ref.read(collectionRepositoryProvider).removeItem(widget.collectionId, designId);
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() => _items = previous);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _move(int index, int direction) async {
    final nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= _items.length) return;

    final previous = _items;
    final reordered = [..._items];
    final moved = reordered.removeAt(index);
    reordered.insert(nextIndex, moved);
    setState(() => _items = reordered);

    try {
      final result = await ref
          .read(collectionRepositoryProvider)
          .reorderItems(widget.collectionId, reordered.map((d) => d.id).toList());
      if (mounted) setState(() => _items = result.items);
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() => _items = previous);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_collection?.name ?? 'Collection'),
        actions: _collection?.isOwner == true
            ? [
                IconButton(icon: const Icon(Icons.edit_outlined), onPressed: _rename),
                IconButton(
                  icon: Icon(
                    _collection!.isPrivate ? Icons.lock_outline : Icons.public,
                  ),
                  onPressed: _togglePrivacy,
                  tooltip: _collection!.isPrivate ? 'Make public' : 'Make private',
                ),
                if (!_collection!.isDefault)
                  IconButton(icon: const Icon(Icons.delete_outline), onPressed: _delete),
              ]
            : null,
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const AppLoadingView(message: 'Loading collection…');
    }
    if (_error != null) {
      return AppErrorState(message: _error!.message, onRetry: _load);
    }
    if (_items.isEmpty) {
      return const AppEmptyState(
        title: 'No designs yet',
        message: 'Add designs to this collection from any design\'s screen.',
        icon: Icons.collections_bookmark_outlined,
      );
    }

    final isOwner = _collection?.isOwner ?? false;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.all(Spacing.s4),
        itemCount: _items.length,
        separatorBuilder: (context, index) => const SizedBox(height: Spacing.s2),
        itemBuilder: (context, index) {
          final design = _items[index];
          return Card(
            child: ListTile(
              leading: SizedBox(
                width: 48,
                height: 48,
                child: design.thumbnailUrl != null
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(Radii.sm),
                        child: Image.network(design.thumbnailUrl!, fit: BoxFit.cover),
                      )
                    : const Icon(Icons.image_outlined),
              ),
              title: Text(design.title),
              trailing: isOwner
                  ? Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.arrow_upward),
                          onPressed: _canReorder && index > 0 ? () => _move(index, -1) : null,
                        ),
                        IconButton(
                          icon: const Icon(Icons.arrow_downward),
                          onPressed: _canReorder && index < _items.length - 1
                              ? () => _move(index, 1)
                              : null,
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => _removeItem(design.id),
                        ),
                      ],
                    )
                  : null,
            ),
          );
        },
      ),
    );
  }
}
