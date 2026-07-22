/// Dart mirror of packages/design-tokens (TypeScript). Values here must stay
/// in sync with that package's color-palette.ts / colors.ts / typography.ts /
/// spacing.ts / radius.ts / shadows.ts / motion.ts / breakpoints.ts /
/// icons.ts — there is no shared codegen between Dart and TypeScript yet, so
/// changes must be applied to both by hand.
library;

import 'package:flutter/widgets.dart';

/// Primitive color scales (see color-palette.ts).
abstract final class HennaPalette {
  static const c50 = Color(0xFFFBF0F1);
  static const c100 = Color(0xFFF6DFE1);
  static const c200 = Color(0xFFEABAC0);
  static const c300 = Color(0xFFDA8D97);
  static const c400 = Color(0xFFC2606E);
  static const c500 = Color(0xFFA43D4E);
  static const c600 = Color(0xFF7A2E3A);
  static const c700 = Color(0xFF5F232C);
  static const c800 = Color(0xFF481B22);
  static const c900 = Color(0xFF331319);
  static const c950 = Color(0xFF200C0F);
}

abstract final class MarigoldPalette {
  static const c50 = Color(0xFFFDF6E9);
  static const c100 = Color(0xFFFAEBC9);
  static const c200 = Color(0xFFF3D48D);
  static const c300 = Color(0xFFEBBB5C);
  static const c400 = Color(0xFFDDA23A);
  static const c500 = Color(0xFFC98A2C);
  static const c600 = Color(0xFFA66E20);
  static const c700 = Color(0xFF82551A);
  static const c800 = Color(0xFF5F3D14);
  static const c900 = Color(0xFF3D280D);
  static const c950 = Color(0xFF251808);
}

abstract final class SandPalette {
  static const c0 = Color(0xFFFFFFFF);
  static const c50 = Color(0xFFFBF7F2);
  static const c100 = Color(0xFFF5EEE6);
  static const c200 = Color(0xFFE8DCD0);
  static const c300 = Color(0xFFD6C4B3);
  static const c400 = Color(0xFFB7A08A);
  static const c500 = Color(0xFF8F7864);
  static const c600 = Color(0xFF6B5847);
  static const c700 = Color(0xFF4F4136);
  static const c800 = Color(0xFF392F27);
  static const c900 = Color(0xFF2B211D);
  static const c950 = Color(0xFF1C1512);
}

abstract final class JadePalette {
  static const c100 = Color(0xFFE1F0EA);
  static const c500 = Color(0xFF2F6F5E);
  static const c700 = Color(0xFF1E4A3F);
}

abstract final class TerracottaPalette {
  static const c100 = Color(0xFFFBE2DC);
  static const c500 = Color(0xFFB3432B);
  static const c700 = Color(0xFF7A2D1D);
}

abstract final class TealPalette {
  static const c100 = Color(0xFFE3EEF3);
  static const c500 = Color(0xFF3B6E8F);
  static const c700 = Color(0xFF284A5F);
}

/// 4px base spacing scale (spacing.ts).
abstract final class Spacing {
  static const s0 = 0.0;
  static const s1 = 4.0;
  static const s2 = 8.0;
  static const s3 = 12.0;
  static const s4 = 16.0;
  static const s5 = 20.0;
  static const s6 = 24.0;
  static const s8 = 32.0;
  static const s10 = 40.0;
  static const s12 = 48.0;
  static const s16 = 64.0;
  static const s20 = 80.0;
  static const s24 = 96.0;
}

/// Corner radii (radius.ts).
abstract final class Radii {
  static const none = 0.0;
  static const sm = 6.0;
  static const md = 10.0;
  static const lg = 16.0;
  static const xl = 24.0;
  static const full = 9999.0;
}

/// Motion durations (motion.ts). Curves mirror the CSS cubic-bezier easings.
abstract final class Motion {
  static const instant = Duration.zero;
  static const fast = Duration(milliseconds: 120);
  static const base = Duration(milliseconds: 200);
  static const slow = Duration(milliseconds: 320);
  static const slower = Duration(milliseconds: 480);

  static const standard = Cubic(0.2, 0, 0, 1);
  static const decelerate = Cubic(0, 0, 0, 1);
  static const accelerate = Cubic(0.3, 0, 1, 1);
}

/// Responsive breakpoints in logical pixels (breakpoints.ts).
abstract final class Breakpoints {
  static const sm = 480.0;
  static const md = 768.0;
  static const lg = 1024.0;
  static const xl = 1280.0;
  static const xxl = 1536.0;

  static bool isCompact(double width) => width < md;
  static bool isMedium(double width) => width >= md && width < lg;
  static bool isExpanded(double width) => width >= lg;
}

/// Icon sizes (icons.ts).
abstract final class IconSizes {
  static const xs = 16.0;
  static const sm = 20.0;
  static const md = 24.0;
  static const lg = 32.0;
  static const xl = 40.0;
}

/// Type scale (typography.ts). Font families are intentionally left as the
/// Flutter/platform default (Roboto/San Francisco) rather than bundling
/// Fraunces/Manrope in this phase — see docs/design-system.md — so the type
/// *scale* (sizes/weights/line-heights) matches the web app even though the
/// *typeface* doesn't yet.
abstract final class FontSizes {
  static const xs = 12.0;
  static const sm = 14.0;
  static const base = 16.0;
  static const lg = 18.0;
  static const xl = 20.0;
  static const x2l = 24.0;
  static const x3l = 30.0;
  static const x4l = 38.0;
  static const x5l = 48.0;
}
