import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Persistent bottom navigation for artist/verified-artist accounts —
/// distinct tab set from [CustomerShell] (dashboard/portfolio instead of
/// discover/collections).
class ArtistShell extends StatelessWidget {
  const ArtistShell({required this.navigationShell, super.key});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (index) => navigationShell.goBranch(
          index,
          initialLocation: index == navigationShell.currentIndex,
        ),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Dashboard'),
          NavigationDestination(
            icon: Icon(Icons.event_available_outlined),
            label: 'Bookings',
          ),
          NavigationDestination(
            icon: Icon(Icons.photo_library_outlined),
            label: 'Portfolio',
          ),
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Messages'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
