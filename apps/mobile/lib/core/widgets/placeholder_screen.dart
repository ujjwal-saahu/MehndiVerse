import 'package:flutter/material.dart';

import 'app_empty_state.dart';

/// A tab body for features not built yet (Phase 4 is UI shells only — see
/// docs/design-system.md). Intentionally shows an empty state rather than
/// invented sample data.
class PlaceholderScreen extends StatelessWidget {
  const PlaceholderScreen({
    required this.title,
    required this.message,
    this.icon = Icons.hourglass_empty,
    super.key,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: AppEmptyState(title: title, message: message, icon: icon),
    );
  }
}
