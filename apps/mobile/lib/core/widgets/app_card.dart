import 'package:flutter/material.dart';

import '../theme/design_tokens.dart';

/// Standard content container. Wraps [Card] (themed in AppTheme) with the
/// padding every card in the app should use, so spacing stays consistent
/// without each screen re-specifying it.
class AppCard extends StatelessWidget {
  const AppCard({
    required this.child,
    this.padding = const EdgeInsets.all(Spacing.s4),
    this.onTap,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    if (onTap == null) {
      return Card(child: Padding(padding: padding, child: child));
    }

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(Radii.lg),
        child: Padding(padding: padding, child: child),
      ),
    );
  }
}
