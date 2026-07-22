import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'preview_models.dart';
import 'preview_repository.dart';

/// "My previews" (`/previews`) — see docs/hand-foot-preview.md.
class PreviewsListScreen extends ConsumerStatefulWidget {
  const PreviewsListScreen({super.key});

  @override
  ConsumerState<PreviewsListScreen> createState() => _PreviewsListScreenState();
}

class _PreviewsListScreenState extends ConsumerState<PreviewsListScreen> {
  Future<List<PreviewProjectData>>? _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() {
      _future = ref.read(previewRepositoryProvider).fetchMine();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My previews')),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await context.push('/previews/new');
          _load();
        },
        child: const Icon(Icons.add_a_photo_outlined),
      ),
      body: FutureBuilder<List<PreviewProjectData>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading previews…');
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return AppErrorState(
              message: error is PreviewException ? error.message : 'Could not load previews.',
              onRetry: _load,
            );
          }
          final previews = snapshot.data!;
          if (previews.isEmpty) {
            return const AppEmptyState(
              title: 'No previews yet',
              message: 'Upload a photo and try a design on it — nothing is saved until you '
                  'choose to.',
            );
          }
          return GridView.builder(
            padding: const EdgeInsets.all(Spacing.s4),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: Spacing.s2,
              mainAxisSpacing: Spacing.s2,
            ),
            itemCount: previews.length,
            itemBuilder: (context, index) {
              final preview = previews[index];
              final imageUrl = preview.resultImageUrl ?? preview.sourceImageUrl;
              return GestureDetector(
                onTap: () async {
                  await context.push('/previews/${preview.id}');
                  _load();
                },
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(Radii.sm),
                  child: Image.network(imageUrl, fit: BoxFit.cover),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
