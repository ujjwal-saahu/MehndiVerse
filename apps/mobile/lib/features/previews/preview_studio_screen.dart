import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../bookings/booking_models.dart';
import '../gallery/gallery_models.dart';
import 'preview_models.dart';
import 'preview_repository.dart';

/// The overlay's width at `scale: 1`, as a fraction of the photo's
/// rendered width — kept identical to apps/web's `BASE_OVERLAY_WIDTH_
/// FRACTION` so a project edited on one platform looks the same on the
/// other. See docs/hand-foot-preview.md#editable-preview-state.
const double _baseOverlayWidthFraction = 0.4;
const int _maxPhotoDimension = 1600; // memory/performance safeguard
const int _maxPhotoBytes = 15 * 1024 * 1024;

/// Hand/foot design preview studio (`/previews/new`, `/previews/:id`) —
/// see docs/hand-foot-preview.md. All move/resize/rotate/flip/opacity
/// editing happens locally via a single pinch-drag-rotate gesture; the
/// photo is only ever uploaded once the user explicitly saves/exports/
/// shares/sends this project.
class PreviewStudioScreen extends ConsumerStatefulWidget {
  const PreviewStudioScreen({this.previewId, super.key});

  final String? previewId;

  @override
  ConsumerState<PreviewStudioScreen> createState() => _PreviewStudioScreenState();
}

class _PreviewStudioScreenState extends ConsumerState<PreviewStudioScreen> {
  final GlobalKey _repaintKey = GlobalKey();
  final ImagePicker _picker = ImagePicker();

  bool _isLoading = false;
  String? _loadError;

  String? _previewId;
  Uint8List? _photoBytes;
  String? _remoteSourceUrl;
  String? _photoError;

  PreviewDesignSummary? _selectedDesign;
  OverlayTransform _transform = const OverlayTransform();
  OverlayTransform? _gestureStartTransform;

  bool _isSaving = false;
  String? _saveError;
  bool _isExporting = false;
  String? _exportError;
  bool _isSharing = false;
  String? _shareMessage;
  bool _isDeleting = false;
  String? _deleteError;

  @override
  void initState() {
    super.initState();
    _previewId = widget.previewId;
    if (_previewId != null) _load(_previewId!);
  }

  void _load(String previewId) {
    setState(() => _isLoading = true);
    ref
        .read(previewRepositoryProvider)
        .fetchOne(previewId)
        .then((data) {
          if (!mounted) return;
          setState(() {
            _remoteSourceUrl = data.sourceImageUrl;
            _selectedDesign = data.design;
            _transform = data.overlayTransform ?? const OverlayTransform();
            _isLoading = false;
          });
        })
        .catchError((Object error) {
          if (!mounted) return;
          setState(() {
            _loadError = 'Could not load this preview project.';
            _isLoading = false;
          });
        });
  }

  Future<void> _pickPhoto() async {
    final picked = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: _maxPhotoDimension.toDouble(),
      maxHeight: _maxPhotoDimension.toDouble(),
      imageQuality: 85,
    );
    if (picked == null) return;

    final bytes = await picked.readAsBytes();
    if (bytes.length > _maxPhotoBytes) {
      setState(() => _photoError = 'That photo is too large (max 15 MB).');
      return;
    }
    setState(() {
      _photoError = null;
      _photoBytes = bytes;
      _remoteSourceUrl = null;
    });
  }

  Future<void> _pickDesign() async {
    final design = await showModalBottomSheet<PreviewDesignSummary>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _DesignPickerSheet(),
    );
    if (design != null) setState(() => _selectedDesign = design);
  }

  void _onScaleStart(ScaleStartDetails details) {
    _gestureStartTransform = _transform;
  }

  void _onScaleUpdate(ScaleUpdateDetails details, Size containerSize) {
    final start = _gestureStartTransform;
    if (start == null || containerSize.width == 0 || containerSize.height == 0) return;
    setState(() {
      final dxFraction = details.focalPointDelta.dx / containerSize.width;
      final dyFraction = details.focalPointDelta.dy / containerSize.height;
      _transform = _transform.copyWith(
        x: (_transform.x + dxFraction).clamp(0.0, 1.0),
        y: (_transform.y + dyFraction).clamp(0.0, 1.0),
        scale: (start.scale * details.scale).clamp(0.2, 5.0),
        rotationDegrees: start.rotationDegrees + details.rotation * 180 / math.pi,
      );
    });
  }

  Future<Uint8List> _captureComposite() async {
    final boundary = _repaintKey.currentContext!.findRenderObject() as RenderRepaintBoundary;
    final image = await boundary.toImage(pixelRatio: 2.0);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    return byteData!.buffer.asUint8List();
  }

  Future<void> _save() async {
    if (_photoBytes == null && _remoteSourceUrl == null) {
      setState(() => _saveError = 'Choose a photo first.');
      return;
    }
    setState(() {
      _isSaving = true;
      _saveError = null;
    });
    try {
      final repository = ref.read(previewRepositoryProvider);
      if (_previewId == null) {
        final created = await repository.create(
          photoBytes: _photoBytes!,
          filename: 'photo.jpg',
          designId: _selectedDesign?.id,
          transform: _transform,
        );
        setState(() {
          _previewId = created.id;
          _remoteSourceUrl = created.sourceImageUrl;
          _photoBytes = null;
        });
      } else {
        final updated = await repository.update(
          _previewId!,
          photoBytes: _photoBytes,
          designId: _selectedDesign?.id,
          transform: _transform,
        );
        setState(() {
          _remoteSourceUrl = updated.sourceImageUrl;
          _photoBytes = null;
        });
      }
      if (mounted) AppSnackBar.showSuccess(context, 'Preview saved.');
    } on PreviewException catch (e) {
      setState(() => _saveError = e.message);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _export() async {
    setState(() {
      _isExporting = true;
      _exportError = null;
    });
    try {
      final bytes = await _captureComposite();
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Exported preview'),
          content: Image.memory(bytes),
          actions: [
            TextButton(onPressed: () => context.pop(), child: const Text('Close')),
          ],
        ),
      );
      if (_previewId != null) {
        await ref.read(previewRepositoryProvider).export(_previewId!, compositeBytes: bytes);
      }
    } on PreviewException catch (e) {
      setState(() => _exportError = e.message);
    } finally {
      if (mounted) setState(() => _isExporting = false);
    }
  }

  Future<void> _share() async {
    if (_previewId == null) {
      setState(() => _shareMessage = 'Save this preview before sharing it.');
      return;
    }
    setState(() {
      _isSharing = true;
      _shareMessage = null;
    });
    try {
      final result = await ref.read(previewRepositoryProvider).share(_previewId!);
      if (!mounted) return;
      // No share-sheet/URL-launcher package exists in this app yet (same
      // gap as the design-download dialog in gallery/design_detail_
      // screen.dart) — surface the signed link so it can be copied.
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Share link'),
          content: SelectableText(result.url),
          actions: [
            TextButton(onPressed: () => context.pop(), child: const Text('Close')),
          ],
        ),
      );
    } on PreviewException catch (e) {
      setState(() => _shareMessage = e.message);
    } finally {
      if (mounted) setState(() => _isSharing = false);
    }
  }

  Future<void> _sendToArtist() async {
    if (_previewId == null) {
      AppSnackBar.showError(context, 'Save this preview before sending it to an artist.');
      return;
    }
    final bookings = await ref.read(bookingRepositoryProvider).fetchMyBookings().catchError(
      (Object _) => <BookingSummaryData>[],
    );
    final active = bookings.where((b) => b.status != 'draft').toList();
    if (!mounted) return;
    final chosen = await showModalBottomSheet<BookingSummaryData>(
      context: context,
      builder: (context) => _BookingPickerSheet(bookings: active),
    );
    if (chosen == null) return;
    try {
      await ref
          .read(previewRepositoryProvider)
          .sendToArtist(_previewId!, bookingId: chosen.id);
      if (mounted) AppSnackBar.showSuccess(context, 'Sent — check your booking messages.');
    } on PreviewException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    }
  }

  Future<void> _delete() async {
    if (_previewId == null) return;
    final confirmed = await showAppConfirmDialog(
      context,
      title: 'Delete preview',
      message: 'This will delete the project and its stored photo. This cannot be undone.',
      confirmLabel: 'Delete',
      isDestructive: true,
    );
    if (!confirmed) return;
    setState(() => _isDeleting = true);
    try {
      await ref.read(previewRepositoryProvider).delete(_previewId!);
      if (mounted) context.pop();
    } on PreviewException catch (e) {
      setState(() {
        _deleteError = e.message;
        _isDeleting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: AppLoadingView(message: 'Loading preview…'));
    }
    if (_loadError != null) {
      return Scaffold(body: AppErrorState(message: _loadError!, onRetry: () => _load(_previewId!)));
    }

    final photoUrl = _remoteSourceUrl;
    final hasPhoto = _photoBytes != null || photoUrl != null;

    return Scaffold(
      appBar: AppBar(title: const Text('Design preview')),
      body: ListView(
        padding: const EdgeInsets.all(Spacing.s4),
        children: [
          Container(
            padding: const EdgeInsets.all(Spacing.s3),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(Radii.md),
            ),
            child: const Text(
              'Your photo stays on this device while you edit — nothing is uploaded yet. '
              'Saving this project uploads it to secure, private storage (only you, and any '
              'artist you explicitly send it to, can view it). You can delete it — and its '
              'stored photo — any time.',
            ),
          ),
          const SizedBox(height: Spacing.s4),
          if (hasPhoto)
            LayoutBuilder(
              builder: (context, constraints) {
                final containerSize = Size(constraints.maxWidth, constraints.maxWidth);
                return RepaintBoundary(
                  key: _repaintKey,
                  child: AspectRatio(
                    aspectRatio: 1,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(Radii.md),
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          Container(color: Colors.black),
                          _photoBytes != null
                              ? Image.memory(_photoBytes!, fit: BoxFit.contain)
                              : Image.network(photoUrl!, fit: BoxFit.contain),
                          if (_selectedDesign?.thumbnailUrl != null)
                            Align(
                              alignment: Alignment(
                                _transform.x * 2 - 1,
                                _transform.y * 2 - 1,
                              ),
                              child: GestureDetector(
                                onScaleStart: _onScaleStart,
                                onScaleUpdate: (details) =>
                                    _onScaleUpdate(details, containerSize),
                                child: Opacity(
                                  opacity: _transform.opacity,
                                  child: Transform(
                                    alignment: Alignment.center,
                                    transform: Matrix4.identity()
                                      ..rotateZ(_transform.rotationDegrees * math.pi / 180)
                                      ..multiply(
                                        Matrix4.diagonal3Values(
                                          _transform.flipHorizontal
                                              ? -_transform.scale
                                              : _transform.scale,
                                          _transform.scale,
                                          1.0,
                                        ),
                                      ),
                                    child: Image.network(
                                      _selectedDesign!.thumbnailUrl!,
                                      width: containerSize.width * _baseOverlayWidthFraction,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            )
          else
            GestureDetector(
              onTap: _pickPhoto,
              child: AspectRatio(
                aspectRatio: 1,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).colorScheme.outline),
                    borderRadius: BorderRadius.circular(Radii.md),
                  ),
                  child: const Center(child: Text('Choose a hand or foot photo')),
                ),
              ),
            ),
          if (_photoError != null)
            Padding(
              padding: const EdgeInsets.only(top: Spacing.s2),
              child: Text(_photoError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          if (hasPhoto) ...[
            const SizedBox(height: Spacing.s3),
            Wrap(
              spacing: Spacing.s2,
              runSpacing: Spacing.s2,
              children: [
                AppSecondaryButton(label: 'Replace photo', onPressed: _pickPhoto),
                AppSecondaryButton(
                  label: _selectedDesign == null
                      ? 'Select a design'
                      : 'Design: ${_selectedDesign!.title}',
                  onPressed: _pickDesign,
                ),
              ],
            ),
          ],
          if (_selectedDesign != null) ...[
            const SizedBox(height: Spacing.s3),
            Row(
              children: [
                Expanded(
                  child: AppSecondaryButton(
                    label: 'Flip overlay',
                    onPressed: () => setState(
                      () => _transform = _transform.copyWith(
                        flipHorizontal: !_transform.flipHorizontal,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: Spacing.s2),
                TextButton(
                  onPressed: () => setState(() => _transform = const OverlayTransform()),
                  child: const Text('Reset'),
                ),
              ],
            ),
            Row(
              children: [
                const Text('Opacity'),
                Expanded(
                  child: Slider(
                    value: _transform.opacity,
                    onChanged: (value) =>
                        setState(() => _transform = _transform.copyWith(opacity: value)),
                  ),
                ),
              ],
            ),
            Text(
              'Drag with one finger to move; pinch and twist with two fingers to resize and '
              'rotate.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          const SizedBox(height: Spacing.s4),
          AppPrimaryButton(
            label: 'Save preview',
            isLoading: _isSaving,
            onPressed: hasPhoto ? _save : null,
          ),
          if (_saveError != null)
            Padding(
              padding: const EdgeInsets.only(top: Spacing.s2),
              child: Text(_saveError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          const SizedBox(height: Spacing.s2),
          Wrap(
            spacing: Spacing.s2,
            runSpacing: Spacing.s2,
            children: [
              AppSecondaryButton(
                label: 'Export image',
                isLoading: _isExporting,
                onPressed: hasPhoto ? _export : null,
              ),
              AppSecondaryButton(
                label: 'Share',
                isLoading: _isSharing,
                onPressed: _previewId != null ? _share : null,
              ),
              AppSecondaryButton(
                label: 'Send to artist',
                onPressed: _previewId != null ? _sendToArtist : null,
              ),
              if (_previewId != null)
                AppSecondaryButton(label: 'Delete', isLoading: _isDeleting, onPressed: _delete),
            ],
          ),
          if (_exportError != null)
            Text(_exportError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (_shareMessage != null) Text(_shareMessage!),
          if (_deleteError != null)
            Text(_deleteError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (_previewId == null)
            Padding(
              padding: const EdgeInsets.only(top: Spacing.s2),
              child: Text(
                'Sharing and sending to an artist need a saved project.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
        ],
      ),
    );
  }
}

class _DesignPickerSheet extends ConsumerStatefulWidget {
  const _DesignPickerSheet();

  @override
  ConsumerState<_DesignPickerSheet> createState() => _DesignPickerSheetState();
}

class _DesignPickerSheetState extends ConsumerState<_DesignPickerSheet> {
  Future<DesignListData>? _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(galleryRepositoryProvider).fetchPublishedDesigns();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: MediaQuery.of(context).size.height * 0.7,
      child: FutureBuilder<DesignListData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading designs…');
          }
          if (snapshot.hasError || snapshot.data == null) {
            return const AppErrorState(message: 'Could not load designs.');
          }
          final designs = snapshot.data!.items;
          if (designs.isEmpty) {
            return const AppEmptyState(title: 'No designs available');
          }
          return GridView.builder(
            padding: const EdgeInsets.all(Spacing.s4),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: Spacing.s2,
              mainAxisSpacing: Spacing.s2,
            ),
            itemCount: designs.length,
            itemBuilder: (context, index) {
              final design = designs[index];
              return GestureDetector(
                onTap: () => context.pop(
                  PreviewDesignSummary(
                    id: design.id,
                    title: design.title,
                    thumbnailUrl: design.thumbnailUrl,
                    isPremium: design.isPremium,
                  ),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(Radii.sm),
                  child: design.thumbnailUrl != null
                      ? Image.network(design.thumbnailUrl!, fit: BoxFit.cover)
                      : Container(color: Theme.of(context).colorScheme.surfaceContainerHighest),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _BookingPickerSheet extends StatelessWidget {
  const _BookingPickerSheet({required this.bookings});

  final List<BookingSummaryData> bookings;

  @override
  Widget build(BuildContext context) {
    if (bookings.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(Spacing.s6),
        child: AppEmptyState(title: 'No active bookings yet'),
      );
    }
    return ListView(
      shrinkWrap: true,
      children: [
        for (final booking in bookings)
          ListTile(
            title: Text(booking.artistDisplayName ?? 'Artist'),
            subtitle: Text(booking.status),
            onTap: () => context.pop(booking),
          ),
      ],
    );
  }
}
