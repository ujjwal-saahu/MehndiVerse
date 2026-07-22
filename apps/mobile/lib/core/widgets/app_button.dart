import 'package:flutter/material.dart';

/// Primary call-to-action button. Wraps [ElevatedButton] (themed in
/// AppTheme) with a built-in loading state so callers don't hand-roll a
/// spinner-vs-label switch on every screen.
class AppPrimaryButton extends StatelessWidget {
  const AppPrimaryButton({
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.icon,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : icon == null
          ? Text(label)
          : Row(
              mainAxisSize: MainAxisSize.min,
              children: [Icon(icon, size: 20), const SizedBox(width: 8), Text(label)],
            ),
    );
  }
}

/// Secondary/alternative action. Wraps [OutlinedButton].
class AppSecondaryButton extends StatelessWidget {
  const AppSecondaryButton({
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Text(label),
    );
  }
}

/// Low-emphasis action (e.g. "Cancel", "Skip"). Wraps [TextButton].
class AppTextActionButton extends StatelessWidget {
  const AppTextActionButton({required this.label, required this.onPressed, super.key});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return TextButton(onPressed: onPressed, child: Text(label));
  }
}
