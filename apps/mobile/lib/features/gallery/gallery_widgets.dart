import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'gallery_models.dart';

/// A single grid/row tile. `Semantics(image: true, label: ...)` gives the
/// design an accessible description even though the underlying `Image`
/// widget carries no `semanticLabel` of its own — see
/// docs/design-gallery.md#accessible-image-descriptions. Shows a plain
/// placeholder instead of a broken image when the thumbnail isn't ready
/// yet, mirroring the web `DesignCard`'s behavior.
class DesignThumbnailCard extends StatelessWidget {
  const DesignThumbnailCard({required this.design, super.key});

  final DesignSummaryData design;

  @override
  Widget build(BuildContext context) {
    final altText = design.artistDisplayName != null
        ? '${design.title} mehndi design by ${design.artistDisplayName}'
        : '${design.title} mehndi design';
    final colors = Theme.of(context).extension<AppColors>() ?? AppColors.light;

    return Semantics(
      label: altText,
      image: true,
      button: true,
      // Without this, the title/artist Text children below would each
      // contribute their own semantics node, and a screen reader would
      // announce the card's label followed by a redundant repeat of the
      // same title/artist text.
      excludeSemantics: true,
      child: GestureDetector(
        onTap: () => context.push('/design/${design.id}'),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(Radii.lg),
          child: AspectRatio(
            aspectRatio: 3 / 4,
            child: Stack(
              fit: StackFit.expand,
              children: [
                if (design.thumbnailUrl != null)
                  Image.network(
                    design.thumbnailUrl!,
                    fit: BoxFit.cover,
                    excludeFromSemantics: true,
                    loadingBuilder: (context, child, progress) =>
                        progress == null ? child : ColoredBox(color: colors.surfaceVariant),
                    errorBuilder: (context, error, stackTrace) =>
                        _Placeholder(colors: colors),
                  )
                else
                  _Placeholder(colors: colors),
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
                          design.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: FontSizes.sm,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (design.artistDisplayName != null)
                          Text(
                            'by ${design.artistDisplayName}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
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
      ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.colors});

  final AppColors colors;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: colors.surfaceVariant,
      child: Icon(
        Icons.image_outlined,
        color: colors.textSecondary.withValues(alpha: 0.4),
        size: IconSizes.lg,
      ),
    );
  }
}

/// Horizontally-scrollable filter chips: "Home" (composite feed), "All
/// Designs" (unfiltered paginated browse), then one chip per category — see
/// docs/design-gallery.md#category-browsing.
class CategoryChipsRow extends StatelessWidget {
  const CategoryChipsRow({
    required this.categories,
    required this.activeKey,
    required this.onSelect,
    super.key,
  });

  final List<CategoryData> categories;
  final String activeKey;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: Spacing.s4, vertical: Spacing.s2),
        children: [
          _chip(label: 'Home', chipKey: 'home'),
          const SizedBox(width: Spacing.s2),
          _chip(label: 'All Designs', chipKey: 'all'),
          for (final category in categories) ...[
            const SizedBox(width: Spacing.s2),
            _chip(label: category.name, chipKey: category.id),
          ],
        ],
      ),
    );
  }

  Widget _chip({required String label, required String chipKey}) {
    return ChoiceChip(
      label: Text(label),
      selected: activeKey == chipKey,
      onSelected: (_) => onSelect(chipKey),
    );
  }
}

/// One labeled, horizontally-scrolling row of the home feed (Latest /
/// Featured / Trending) — see docs/design-gallery.md#home-feed.
class DesignSectionRow extends StatelessWidget {
  const DesignSectionRow({required this.title, required this.designs, super.key});

  final String title;
  final List<DesignSummaryData> designs;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.s6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.s4),
            child: Text(title, style: Theme.of(context).textTheme.titleLarge),
          ),
          const SizedBox(height: Spacing.s3),
          SizedBox(
            height: 220,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: Spacing.s4),
              itemCount: designs.length,
              separatorBuilder: (context, index) => const SizedBox(width: Spacing.s3),
              itemBuilder: (context, index) =>
                  SizedBox(width: 160, child: DesignThumbnailCard(design: designs[index])),
            ),
          ),
        ],
      ),
    );
  }
}

/// Compact artist card shown on the design-detail screen — see
/// docs/design-gallery.md#artist-summary.
class ArtistSummaryTile extends StatelessWidget {
  const ArtistSummaryTile({required this.artist, super.key});

  final ArtistSummaryData artist;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Row(
        children: [
          CircleAvatar(
            radius: 24,
            backgroundImage: artist.avatarUrl != null ? NetworkImage(artist.avatarUrl!) : null,
            child: artist.avatarUrl == null ? const Icon(Icons.person) : null,
          ),
          const SizedBox(width: Spacing.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(artist.displayName, style: Theme.of(context).textTheme.titleMedium),
                if (artist.headline != null)
                  Text(
                    artist.headline!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
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
  }
}

/// Main image + thumbnail strip, tap to open a full-screen pinch-to-zoom
/// view — see docs/design-gallery.md#image-gallery-and-zoom. Only `ready`
/// images are ever passed in by the caller (`design.readyImages`).
class DesignImageGallery extends StatefulWidget {
  const DesignImageGallery({required this.images, required this.title, super.key});

  final List<DesignImageData> images;
  final String title;

  @override
  State<DesignImageGallery> createState() => _DesignImageGalleryState();
}

class _DesignImageGalleryState extends State<DesignImageGallery> {
  int _activeIndex = 0;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AppColors>() ?? AppColors.light;

    if (widget.images.isEmpty) {
      return Semantics(
        label: '${widget.title} mehndi design — image not yet available',
        image: true,
        child: AspectRatio(
          aspectRatio: 1,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(Radii.lg),
            child: ColoredBox(
              color: colors.surfaceVariant,
              child: Center(
                child: Text('Image coming soon', style: TextStyle(color: colors.textSecondary)),
              ),
            ),
          ),
        ),
      );
    }

    final active = widget.images[_activeIndex];

    return Column(
      children: [
        Semantics(
          label:
              '${widget.title} mehndi design, image ${_activeIndex + 1} of '
              '${widget.images.length}. Double tap to zoom.',
          image: true,
          button: true,
          child: GestureDetector(
            onTap: () => _openZoom(context),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(Radii.lg),
              child: AspectRatio(
                aspectRatio: 1,
                child: Image.network(
                  active.thumbnailMediumUrl ?? active.imageUrl!,
                  fit: BoxFit.cover,
                  excludeFromSemantics: true,
                ),
              ),
            ),
          ),
        ),
        if (widget.images.length > 1) ...[
          const SizedBox(height: Spacing.s3),
          SizedBox(
            height: 64,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: widget.images.length,
              separatorBuilder: (context, index) => const SizedBox(width: Spacing.s2),
              itemBuilder: (context, index) {
                final image = widget.images[index];
                final selected = index == _activeIndex;
                return GestureDetector(
                  onTap: () => setState(() => _activeIndex = index),
                  child: Container(
                    width: 64,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(Radii.md),
                      border: Border.all(
                        color: selected ? Theme.of(context).colorScheme.primary : Colors.transparent,
                        width: 2,
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(Radii.md - 2),
                      child: Image.network(
                        image.thumbnailSmallUrl ?? image.imageUrl!,
                        fit: BoxFit.cover,
                        excludeFromSemantics: true,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ],
    );
  }

  void _openZoom(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (context) =>
            _ZoomedImageView(images: widget.images, initialIndex: _activeIndex, title: widget.title),
      ),
    );
  }
}

class _ZoomedImageView extends StatefulWidget {
  const _ZoomedImageView({required this.images, required this.initialIndex, required this.title});

  final List<DesignImageData> images;
  final int initialIndex;
  final String title;

  @override
  State<_ZoomedImageView> createState() => _ZoomedImageViewState();
}

class _ZoomedImageViewState extends State<_ZoomedImageView> {
  late final PageController _pageController = PageController(initialPage: widget.initialIndex);
  late int _currentIndex = widget.initialIndex;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        iconTheme: const IconThemeData(color: Colors.white),
        title: Text(
          '${_currentIndex + 1} of ${widget.images.length}',
          style: const TextStyle(color: Colors.white),
        ),
      ),
      body: PageView.builder(
        controller: _pageController,
        itemCount: widget.images.length,
        onPageChanged: (index) => setState(() => _currentIndex = index),
        itemBuilder: (context, index) {
          final image = widget.images[index];
          return Semantics(
            label:
                '${widget.title} mehndi design, zoomed in, image ${index + 1} of '
                '${widget.images.length}',
            image: true,
            child: InteractiveViewer(
              minScale: 1,
              maxScale: 4,
              child: Center(
                child: Image.network(
                  image.imageUrl ?? image.thumbnailMediumUrl!,
                  excludeFromSemantics: true,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
