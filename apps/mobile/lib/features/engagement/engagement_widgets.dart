import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../gallery/gallery_repository.dart' show GalleryException;

/// Like/save toggles on the design-detail screen — see
/// docs/engagement-and-collections.md#optimistic-ui. Both buttons flip
/// immediately on tap (optimistic) and roll back to the pre-tap state if the
/// backend call fails, mirroring the web `LikeSaveButtons` component.
class LikeSaveButtons extends ConsumerStatefulWidget {
  const LikeSaveButtons({
    required this.designId,
    required this.initialIsLiked,
    required this.initialLikeCount,
    required this.initialIsSaved,
    required this.initialSaveCount,
    super.key,
  });

  final String designId;
  final bool initialIsLiked;
  final int initialLikeCount;
  final bool initialIsSaved;
  final int initialSaveCount;

  @override
  ConsumerState<LikeSaveButtons> createState() => _LikeSaveButtonsState();
}

class _LikeSaveButtonsState extends ConsumerState<LikeSaveButtons> {
  late bool _isLiked = widget.initialIsLiked;
  late int _likeCount = widget.initialLikeCount;
  String? _likeError;
  bool _isLikePending = false;

  late bool _isSaved = widget.initialIsSaved;
  late int _saveCount = widget.initialSaveCount;
  String? _saveError;
  bool _isSavePending = false;

  Future<void> _toggleLike() async {
    if (_isLikePending) return;
    final previousLiked = _isLiked;
    final previousCount = _likeCount;
    final nextLiked = !_isLiked;

    setState(() {
      _isLiked = nextLiked;
      _likeCount = previousCount + (nextLiked ? 1 : -1);
      _likeError = null;
      _isLikePending = true;
    });

    try {
      final repository = ref.read(engagementRepositoryProvider);
      final result = nextLiked
          ? await repository.like(widget.designId)
          : await repository.unlike(widget.designId);
      if (!mounted) return;
      setState(() {
        _isLiked = result.liked;
        _likeCount = result.likeCount;
      });
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLiked = previousLiked;
        _likeCount = previousCount;
        _likeError = e.message;
      });
    } finally {
      if (mounted) setState(() => _isLikePending = false);
    }
  }

  Future<void> _toggleSave() async {
    if (_isSavePending) return;
    final previousSaved = _isSaved;
    final previousCount = _saveCount;
    final nextSaved = !_isSaved;

    setState(() {
      _isSaved = nextSaved;
      _saveCount = previousCount + (nextSaved ? 1 : -1);
      _saveError = null;
      _isSavePending = true;
    });

    try {
      final repository = ref.read(engagementRepositoryProvider);
      final result = nextSaved
          ? await repository.save(widget.designId)
          : await repository.unsave(widget.designId);
      if (!mounted) return;
      setState(() {
        _isSaved = result.saved;
        _saveCount = result.saveCount;
      });
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() {
        _isSaved = previousSaved;
        _saveCount = previousCount;
        _saveError = e.message;
      });
    } finally {
      if (mounted) setState(() => _isSavePending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: Spacing.s2,
          children: [
            _ToggleChip(
              label: _isLiked ? 'Liked' : 'Like',
              count: _likeCount,
              active: _isLiked,
              onPressed: _isLikePending ? null : _toggleLike,
            ),
            _ToggleChip(
              label: _isSaved ? 'Saved' : 'Save',
              count: _saveCount,
              active: _isSaved,
              onPressed: _isSavePending ? null : _toggleSave,
            ),
          ],
        ),
        if (_likeError != null)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s1),
            child: Text(_likeError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
        if (_saveError != null)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s1),
            child: Text(_saveError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
      ],
    );
  }
}

class _ToggleChip extends StatelessWidget {
  const _ToggleChip({
    required this.label,
    required this.count,
    required this.active,
    required this.onPressed,
  });

  final String label;
  final int count;
  final bool active;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text('$label · $count'),
      selected: active,
      onSelected: onPressed == null ? null : (_) => onPressed!(),
    );
  }
}
