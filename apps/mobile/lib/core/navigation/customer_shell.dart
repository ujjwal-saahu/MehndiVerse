import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Persistent bottom navigation for customer-role accounts. Each branch
/// keeps its own navigation stack/scroll position via
/// [StatefulNavigationShell] (GoRouter's `StatefulShellRoute.indexedStack`).
class CustomerShell extends StatelessWidget {
  const CustomerShell({required this.navigationShell, super.key});

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
          NavigationDestination(
            icon: Icon(Icons.auto_awesome_outlined),
            label: 'Discover',
          ),
          NavigationDestination(icon: Icon(Icons.bookmark_border), label: 'Collections'),
          NavigationDestination(
            icon: Icon(Icons.event_available_outlined),
            label: 'Bookings',
          ),
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Messages'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
