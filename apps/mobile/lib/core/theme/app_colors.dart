import 'package:flutter/material.dart';

import 'design_tokens.dart';

/// Semantic color tokens (mirrors colors.ts::SemanticColors). Access via
/// `Theme.of(context).extension<AppColors>()!` rather than hard-coding a
/// palette color directly in a widget.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.background,
    required this.surface,
    required this.surfaceVariant,
    required this.border,
    required this.textPrimary,
    required this.textSecondary,
    required this.textOnPrimary,
    required this.textOnAccent,
    required this.primary,
    required this.primaryHover,
    required this.primaryPressed,
    required this.accent,
    required this.accentHover,
    required this.success,
    required this.successSurface,
    required this.warning,
    required this.warningSurface,
    required this.danger,
    required this.dangerSurface,
    required this.info,
    required this.infoSurface,
    required this.focusRing,
  });

  final Color background;
  final Color surface;
  final Color surfaceVariant;
  final Color border;
  final Color textPrimary;
  final Color textSecondary;
  final Color textOnPrimary;
  final Color textOnAccent;
  final Color primary;
  final Color primaryHover;
  final Color primaryPressed;
  final Color accent;
  final Color accentHover;
  final Color success;
  final Color successSurface;
  final Color warning;
  final Color warningSurface;
  final Color danger;
  final Color dangerSurface;
  final Color info;
  final Color infoSurface;
  final Color focusRing;

  static const light = AppColors(
    background: SandPalette.c50,
    surface: SandPalette.c0,
    surfaceVariant: SandPalette.c100,
    border: SandPalette.c200,
    textPrimary: SandPalette.c900,
    textSecondary: SandPalette.c600,
    textOnPrimary: SandPalette.c50,
    textOnAccent: SandPalette.c950,
    primary: HennaPalette.c600,
    primaryHover: HennaPalette.c700,
    primaryPressed: HennaPalette.c800,
    accent: MarigoldPalette.c500,
    accentHover: MarigoldPalette.c600,
    success: JadePalette.c500,
    successSurface: JadePalette.c100,
    warning: MarigoldPalette.c500,
    warningSurface: MarigoldPalette.c100,
    danger: TerracottaPalette.c500,
    dangerSurface: TerracottaPalette.c100,
    info: TealPalette.c500,
    infoSurface: TealPalette.c100,
    focusRing: TealPalette.c500,
  );

  static const dark = AppColors(
    background: SandPalette.c950,
    surface: Color(0xFF241C18),
    surfaceVariant: SandPalette.c900,
    border: SandPalette.c800,
    textPrimary: SandPalette.c50,
    textSecondary: SandPalette.c300,
    textOnPrimary: SandPalette.c950,
    textOnAccent: SandPalette.c950,
    primary: HennaPalette.c300,
    primaryHover: HennaPalette.c200,
    primaryPressed: HennaPalette.c100,
    accent: MarigoldPalette.c300,
    accentHover: MarigoldPalette.c200,
    success: JadePalette.c100,
    successSurface: JadePalette.c700,
    warning: MarigoldPalette.c300,
    warningSurface: MarigoldPalette.c700,
    danger: TerracottaPalette.c100,
    dangerSurface: TerracottaPalette.c700,
    info: TealPalette.c100,
    infoSurface: TealPalette.c700,
    focusRing: TealPalette.c100,
  );

  @override
  AppColors copyWith({
    Color? background,
    Color? surface,
    Color? surfaceVariant,
    Color? border,
    Color? textPrimary,
    Color? textSecondary,
    Color? textOnPrimary,
    Color? textOnAccent,
    Color? primary,
    Color? primaryHover,
    Color? primaryPressed,
    Color? accent,
    Color? accentHover,
    Color? success,
    Color? successSurface,
    Color? warning,
    Color? warningSurface,
    Color? danger,
    Color? dangerSurface,
    Color? info,
    Color? infoSurface,
    Color? focusRing,
  }) {
    return AppColors(
      background: background ?? this.background,
      surface: surface ?? this.surface,
      surfaceVariant: surfaceVariant ?? this.surfaceVariant,
      border: border ?? this.border,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textOnPrimary: textOnPrimary ?? this.textOnPrimary,
      textOnAccent: textOnAccent ?? this.textOnAccent,
      primary: primary ?? this.primary,
      primaryHover: primaryHover ?? this.primaryHover,
      primaryPressed: primaryPressed ?? this.primaryPressed,
      accent: accent ?? this.accent,
      accentHover: accentHover ?? this.accentHover,
      success: success ?? this.success,
      successSurface: successSurface ?? this.successSurface,
      warning: warning ?? this.warning,
      warningSurface: warningSurface ?? this.warningSurface,
      danger: danger ?? this.danger,
      dangerSurface: dangerSurface ?? this.dangerSurface,
      info: info ?? this.info,
      infoSurface: infoSurface ?? this.infoSurface,
      focusRing: focusRing ?? this.focusRing,
    );
  }

  @override
  AppColors lerp(ThemeExtension<AppColors>? other, double t) {
    if (other is! AppColors) return this;
    return AppColors(
      background: Color.lerp(background, other.background, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceVariant: Color.lerp(surfaceVariant, other.surfaceVariant, t)!,
      border: Color.lerp(border, other.border, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textOnPrimary: Color.lerp(textOnPrimary, other.textOnPrimary, t)!,
      textOnAccent: Color.lerp(textOnAccent, other.textOnAccent, t)!,
      primary: Color.lerp(primary, other.primary, t)!,
      primaryHover: Color.lerp(primaryHover, other.primaryHover, t)!,
      primaryPressed: Color.lerp(primaryPressed, other.primaryPressed, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentHover: Color.lerp(accentHover, other.accentHover, t)!,
      success: Color.lerp(success, other.success, t)!,
      successSurface: Color.lerp(successSurface, other.successSurface, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      warningSurface: Color.lerp(warningSurface, other.warningSurface, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      dangerSurface: Color.lerp(dangerSurface, other.dangerSurface, t)!,
      info: Color.lerp(info, other.info, t)!,
      infoSurface: Color.lerp(infoSurface, other.infoSurface, t)!,
      focusRing: Color.lerp(focusRing, other.focusRing, t)!,
    );
  }
}
