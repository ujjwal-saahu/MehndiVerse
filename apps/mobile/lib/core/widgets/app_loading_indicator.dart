import 'package:flutter/material.dart';

import '../theme/design_tokens.dart';

/// Standard loading spinner, sized off the icon-size scale so it lines up
/// visually with icon buttons elsewhere in the app.
class AppLoadingIndicator extends StatelessWidget {
  const AppLoadingIndicator({this.size = IconSizes.lg, super.key});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SizedBox(
        height: size,
        width: size,
        child: const CircularProgressIndicator(strokeWidth: 3),
      ),
    );
  }
}

/// Full-page loading state — a centered [AppLoadingIndicator] with an
/// optional caption, for screens waiting on a first data fetch.
class AppLoadingView extends StatelessWidget {
  const AppLoadingView({this.message, super.key});

  final String? message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const AppLoadingIndicator(),
          if (message != null) ...[
            const SizedBox(height: Spacing.s3),
            Text(message!, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ],
      ),
    );
  }
}
