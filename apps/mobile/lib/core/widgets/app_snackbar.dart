import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Centralized snackbar presentation so every screen shows success/error/info
/// feedback consistently instead of constructing raw [SnackBar]s inline.
abstract final class AppSnackBar {
  static void showSuccess(BuildContext context, String message) {
    _show(context, message, background: _colors(context).success, foreground: _colors(context).successSurface);
  }

  static void showError(BuildContext context, String message) {
    _show(context, message, background: _colors(context).danger, foreground: _colors(context).dangerSurface);
  }

  static void showInfo(BuildContext context, String message) {
    _show(context, message, background: _colors(context).info, foreground: _colors(context).infoSurface);
  }

  static AppColors _colors(BuildContext context) =>
      Theme.of(context).extension<AppColors>() ?? AppColors.light;

  static void _show(
    BuildContext context,
    String message, {
    required Color background,
    required Color foreground,
  }) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          backgroundColor: background,
          content: Text(message, style: TextStyle(color: foreground)),
        ),
      );
  }
}
