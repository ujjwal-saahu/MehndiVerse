import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import 'collection_models.dart';

/// "Add design to collection" — a modal bottom sheet listing the user's own
/// named collections (the default "Saved Designs" collection is handled by
/// the Save button, not this menu). Tapping a collection is idempotent —
/// safe even if the design is already in it. See
/// docs/engagement-and-collections.md.
class AddToCollectionSheet extends ConsumerStatefulWidget {
  const AddToCollectionSheet({required this.designId, super.key});

  final String designId;

  @override
  ConsumerState<AddToCollectionSheet> createState() => _AddToCollectionSheetState();
}

class _AddToCollectionSheetState extends ConsumerState<AddToCollectionSheet> {
  List<CollectionData>? _collections;
  final Set<String> _addedIds = {};
  String? _error;

  @override
  void initState() {
    super.initState();
    ref
        .read(collectionRepositoryProvider)
        .fetchMyCollections(limit: 50)
        .then((data) {
          if (mounted) {
            setState(
              () => _collections = data.items.where((c) => !c.isDefault).toList(),
            );
          }
        })
        .catchError((Object _) {
          if (mounted) setState(() => _error = 'Could not load your collections.');
        });
  }

  Future<void> _addTo(String collectionId) async {
    try {
      await ref.read(collectionRepositoryProvider).addItem(collectionId, widget.designId);
      if (mounted) setState(() => _addedIds.add(collectionId));
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not add this design. Try again.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.s4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Add to collection', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: Spacing.s3),
            if (_collections == null)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: Spacing.s4),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_collections!.isEmpty)
              const Text("You don't have any collections yet.")
            else
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _collections!.length,
                  itemBuilder: (context, index) {
                    final collection = _collections![index];
                    final added = _addedIds.contains(collection.id);
                    return ListTile(
                      title: Text(collection.name),
                      trailing: added ? const Icon(Icons.check) : null,
                      onTap: added ? null : () => _addTo(collection.id),
                    );
                  },
                ),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: Spacing.s2),
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

void showAddToCollectionSheet(BuildContext context, String designId) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) => AddToCollectionSheet(designId: designId),
  );
}
