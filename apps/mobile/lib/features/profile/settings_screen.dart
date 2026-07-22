import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.workspace_premium_outlined),
            title: const Text('Subscription'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/subscription'),
          ),
          ListTile(
            leading: const Icon(Icons.image_outlined),
            title: const Text('Design preview studio'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/previews'),
          ),
          ListTile(
            leading: const Icon(Icons.language),
            title: const Text('Language'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/settings/language'),
          ),
          ListTile(
            leading: const Icon(Icons.notifications_outlined),
            title: const Text('Notifications'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/settings/notifications'),
          ),
          ListTile(
            leading: const Icon(Icons.lock_outline),
            title: const Text('Privacy'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/settings/privacy'),
          ),
          ListTile(
            leading: const Icon(Icons.block),
            title: const Text('Blocked users'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/settings/blocked-users'),
          ),
        ],
      ),
    );
  }
}
