import 'package:flutter/material.dart';

import '../../core/widgets/widgets.dart';

class BookingsScreen extends StatelessWidget {
  const BookingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PlaceholderScreen(
      title: 'Bookings',
      message: 'Your booking requests and confirmations will appear here.',
      icon: Icons.event_available_outlined,
    );
  }
}
