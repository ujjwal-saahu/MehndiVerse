import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/widgets/widgets.dart';
import 'profile_models.dart';
import 'profile_repository.dart';

class BlockedUsersScreen extends ConsumerStatefulWidget {
  const BlockedUsersScreen({super.key});

  @override
  ConsumerState<BlockedUsersScreen> createState() => _BlockedUsersScreenState();
}

class _BlockedUsersScreenState extends ConsumerState<BlockedUsersScreen> {
  late Future<List<BlockedUser>> _blockedFuture;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _blockedFuture = ref.read(profileRepositoryProvider).fetchBlockedUsers();
  }

  Future<void> _unblock(BlockedUser user) async {
    try {
      await ref.read(profileRepositoryProvider).unblockUser(user.userId);
      setState(_load);
      if (mounted) {
        AppSnackBar.showSuccess(
          context,
          '${user.displayName ?? 'User'} unblocked.',
        );
      }
    } on ProfileException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Blocked users')),
      body: FutureBuilder<List<BlockedUser>>(
        future: _blockedFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView();
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as ProfileException?)?.message ?? 'Could not load.',
              onRetry: () => setState(_load),
            );
          }

          final blocked = snapshot.data!;
          if (blocked.isEmpty) {
            return const AppEmptyState(
              title: 'No blocked users',
              message: "You haven't blocked anyone.",
              icon: Icons.block,
            );
          }

          return ListView.builder(
            itemCount: blocked.length,
            itemBuilder: (context, index) {
              final user = blocked[index];
              return ListTile(
                leading: const Icon(Icons.person),
                title: Text(user.displayName ?? 'Unknown user'),
                trailing: TextButton(
                  onPressed: () => _unblock(user),
                  child: const Text('Unblock'),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
