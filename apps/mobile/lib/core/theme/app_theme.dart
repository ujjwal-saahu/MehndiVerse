import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'design_tokens.dart';

/// Builds the app's light and dark [ThemeData] from the shared design
/// tokens. See docs/design-system.md for the visual-identity rationale.
abstract final class AppTheme {
  static ThemeData get light => _build(AppColors.light, Brightness.light);
  static ThemeData get dark => _build(AppColors.dark, Brightness.dark);

  static ThemeData _build(AppColors colors, Brightness brightness) {
    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: colors.primary,
      onPrimary: colors.textOnPrimary,
      secondary: colors.accent,
      onSecondary: colors.textOnAccent,
      error: colors.danger,
      onError: colors.textOnPrimary,
      surface: colors.surface,
      onSurface: colors.textPrimary,
      surfaceContainerHighest: colors.surfaceVariant,
      outline: colors.border,
    );

    final textTheme = _textTheme(colors.textPrimary, colors.textSecondary);

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: colors.background,
      textTheme: textTheme,
      extensions: [colors],
      appBarTheme: AppBarTheme(
        backgroundColor: colors.background,
        foregroundColor: colors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge,
      ),
      cardTheme: CardThemeData(
        color: colors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.lg),
          side: BorderSide(color: colors.border),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: colors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.lg)),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colors.primary,
          foregroundColor: colors.textOnPrimary,
          disabledBackgroundColor: colors.border,
          disabledForegroundColor: colors.textSecondary,
          padding: const EdgeInsets.symmetric(horizontal: Spacing.s6, vertical: Spacing.s4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.md)),
          textStyle: textTheme.labelLarge,
          minimumSize: const Size(64, 48),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colors.primary,
          side: BorderSide(color: colors.border),
          padding: const EdgeInsets.symmetric(horizontal: Spacing.s6, vertical: Spacing.s4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.md)),
          textStyle: textTheme.labelLarge,
          minimumSize: const Size(64, 48),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: colors.primary,
          padding: const EdgeInsets.symmetric(horizontal: Spacing.s3, vertical: Spacing.s2),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.md)),
          textStyle: textTheme.labelLarge,
          minimumSize: const Size(48, 44),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colors.surfaceVariant,
        contentPadding: const EdgeInsets.symmetric(horizontal: Spacing.s4, vertical: Spacing.s3),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(Radii.md),
          borderSide: BorderSide(color: colors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(Radii.md),
          borderSide: BorderSide(color: colors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(Radii.md),
          borderSide: BorderSide(color: colors.focusRing, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(Radii.md),
          borderSide: BorderSide(color: colors.danger),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(Radii.md),
          borderSide: BorderSide(color: colors.danger, width: 2),
        ),
        labelStyle: TextStyle(color: colors.textSecondary),
        hintStyle: TextStyle(color: colors.textSecondary),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: colors.textPrimary,
        contentTextStyle: textTheme.bodyMedium?.copyWith(color: colors.background),
        actionTextColor: colors.accent,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.md)),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: colors.surface,
        selectedItemColor: colors.primary,
        unselectedItemColor: colors.textSecondary,
        type: BottomNavigationBarType.fixed,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: colors.surface,
        indicatorColor: colors.primary.withValues(alpha: 0.12),
      ),
      dividerTheme: DividerThemeData(color: colors.border, space: 1),
      progressIndicatorTheme: ProgressIndicatorThemeData(color: colors.primary),
    );
  }

  static TextTheme _textTheme(Color primaryText, Color secondaryText) {
    TextStyle style(double size, FontWeight weight, {Color? color}) {
      return TextStyle(fontSize: size, fontWeight: weight, color: color ?? primaryText);
    }

    return TextTheme(
      displayLarge: style(FontSizes.x5l, FontWeight.w700),
      displayMedium: style(FontSizes.x4l, FontWeight.w700),
      displaySmall: style(FontSizes.x3l, FontWeight.w600),
      headlineLarge: style(FontSizes.x3l, FontWeight.w600),
      headlineMedium: style(FontSizes.x2l, FontWeight.w600),
      headlineSmall: style(FontSizes.xl, FontWeight.w600),
      titleLarge: style(FontSizes.xl, FontWeight.w600),
      titleMedium: style(FontSizes.lg, FontWeight.w600),
      titleSmall: style(FontSizes.base, FontWeight.w600),
      bodyLarge: style(FontSizes.lg, FontWeight.w400),
      bodyMedium: style(FontSizes.base, FontWeight.w400),
      bodySmall: style(FontSizes.sm, FontWeight.w400, color: secondaryText),
      labelLarge: style(FontSizes.base, FontWeight.w600),
      labelMedium: style(FontSizes.sm, FontWeight.w600),
      labelSmall: style(FontSizes.xs, FontWeight.w600, color: secondaryText),
    );
  }
}
