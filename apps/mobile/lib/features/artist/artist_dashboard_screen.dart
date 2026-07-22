import 'package:flutter/material.dart';

import '../../core/widgets/widgets.dart';

class ArtistDashboardScreen extends StatelessWidget {
  const ArtistDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PlaceholderScreen(
      title: 'Dashboard',
      message: 'Booking requests, earnings, and reviews will appear here once artist profiles ship.',
      icon: Icons.dashboard_outlined,
    );
  }
}
