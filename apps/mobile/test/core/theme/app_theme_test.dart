import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';

void main() {
  test('light theme uses light brightness and exposes AppColors', () {
    final theme = AppTheme.light;

    expect(theme.brightness, Brightness.light);
    final colors = theme.extension<AppColors>();
    expect(colors, isNotNull);
    expect(colors!.background, AppColors.light.background);
  });

  test('dark theme uses dark brightness and exposes AppColors', () {
    final theme = AppTheme.dark;

    expect(theme.brightness, Brightness.dark);
    final colors = theme.extension<AppColors>();
    expect(colors, isNotNull);
    expect(colors!.background, AppColors.dark.background);
  });

  test('light and dark themes use distinct background colors', () {
    expect(AppTheme.light.scaffoldBackgroundColor, isNot(AppTheme.dark.scaffoldBackgroundColor));
  });
}
