import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'messaging_models.dart';
import 'messaging_repository.dart';

/// Conversation list — see docs/booking-messaging.md. Shared by both the
/// customer and artist shells (`/messages` and `/artist/messages` both
/// route here): a conversation's "other party" is resolved server-side
/// relative to whoever is asking, so the same screen works for either role.
class MessagesScreen extends ConsumerStatefulWidget {
  const MessagesScreen({super.key});

  @override
  ConsumerState<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends ConsumerState<MessagesScreen> {
  late Future<List<ConversationSummaryData>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(messagingRepositoryProvider).fetchConversations();
  }

  void _reload() {
    setState(() {
      _future = ref.read(messagingRepositoryProvider).fetchConversations();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Messages')),
      body: FutureBuilder<List<ConversationSummaryData>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading conversations…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as MessagingException?)?.message ??
                  'Could not load your conversations.',
              onRetry: _reload,
            );
          }

          final conversations = snapshot.data!;
          if (conversations.isEmpty) {
            return const PlaceholderScreen(
              title: 'Messages',
              message: 'Conversations about your bookings will appear here.',
              icon: Icons.chat_bubble_outline,
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(Spacing.s4),
            itemCount: conversations.length,
            separatorBuilder: (context, index) => const SizedBox(height: Spacing.s2),
            itemBuilder: (context, index) {
              final conversation = conversations[index];
              return AppCard(
                onTap: () => context.push('/messages/${conversation.booking.bookingId}'),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            [
                              conversation.otherPartyDisplayName ?? 'Conversation',
                              if (conversation.booking.serviceName != null)
                                conversation.booking.serviceName!,
                            ].join(' · '),
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          const SizedBox(height: Spacing.s1),
                          Text(
                            conversation.lastMessagePreview ?? 'No messages yet',
                            style: Theme.of(context).textTheme.bodySmall,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    if (conversation.unreadCount > 0)
                      CircleAvatar(
                        radius: 10,
                        child: Text(
                          '${conversation.unreadCount}',
                          style: const TextStyle(fontSize: FontSizes.xs),
                        ),
                      ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}
