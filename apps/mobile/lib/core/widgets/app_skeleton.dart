import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/design_tokens.dart';

/// A shimmering placeholder box shown while real content is loading. Built
/// on a plain [AnimatedBuilder] + gradient sweep rather than pulling in a
/// third-party shimmer package, since the effect is simple enough not to
/// need one.
class AppSkeleton extends StatefulWidget {
  const AppSkeleton({
    this.width,
    this.height = 16,
    this.borderRadius = Radii.sm,
    super.key,
  });

  /// A skeleton standing in for a circular avatar.
  const AppSkeleton.circle({required double diameter, super.key})
    : width = diameter,
      height = diameter,
      borderRadius = diameter / 2;

  final double? width;
  final double height;
  final double borderRadius;

  @override
  State<AppSkeleton> createState() => _AppSkeletonState();
}

class _AppSkeletonState extends State<AppSkeleton> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))
      ..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AppColors>() ?? AppColors.light;

    return Semantics(
      label: 'Loading',
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return ShaderMask(
            shaderCallback: (bounds) {
              return LinearGradient(
                colors: [colors.surfaceVariant, colors.border, colors.surfaceVariant],
                stops: const [0.35, 0.5, 0.65],
                begin: Alignment(-1 + 2 * _controller.value * 2, 0),
                end: Alignment(1 + 2 * _controller.value * 2, 0),
              ).createShader(bounds);
            },
            child: Container(
              width: widget.width,
              height: widget.height,
              decoration: BoxDecoration(
                color: colors.surfaceVariant,
                borderRadius: BorderRadius.circular(widget.borderRadius),
              ),
            ),
          );
        },
      ),
    );
  }
}
