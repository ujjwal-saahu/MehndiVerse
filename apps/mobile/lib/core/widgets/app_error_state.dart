import 'package:flutter/material.dart';

import '../theme/design_tokens.dart';
import 'app_button.dart';

/// Shown when a screen failed to load its data. Distinct from
/// [AppEmptyState] (which is "loaded successfully, nothing there") — this is
/// "failed to load", and always offers a retry action.
class AppErrorState extends StatelessWidget {
  const AppErrorState({
    required this.message,
    this.onRetry,
    this.title = 'Something went wrong',
    super.key,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.s6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: IconSizes.xl, color: theme.colorScheme.error),
            const SizedBox(height: Spacing.s4),
            Text(title, style: theme.textTheme.titleMedium, textAlign: TextAlign.center),
            const SizedBox(height: Spacing.s2),
            Text(message, style: theme.textTheme.bodyMedium, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: Spacing.s4),
              AppSecondaryButton(label: 'Try again', onPressed: onRetry),
            ],
          ],
        ),
      ),
    );
  }
}
