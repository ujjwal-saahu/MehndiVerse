import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'messaging_models.dart';
import 'messaging_repository.dart';

/// A single booking's message thread — see docs/booking-messaging.md.
/// Read-and-write for both parties; "the other party" is whoever isn't the
/// caller, resolved server-side.
class ConversationDetailScreen extends ConsumerStatefulWidget {
  const ConversationDetailScreen({required this.bookingId, super.key});

  final String bookingId;

  @override
  ConsumerState<ConversationDetailScreen> createState() => _ConversationDetailScreenState();
}

class _ConversationDetailScreenState extends ConsumerState<ConversationDetailScreen> {
  late Future<MessagePageData> _future;
  final _textController = TextEditingController();
  bool _isBusy = false;

  @override
  void initState() {
    super.initState();
    _future = _loadInitial();
  }

  Future<MessagePageData> _loadInitial() async {
    final repository = ref.read(messagingRepositoryProvider);
    final page = await repository.fetchMessages(widget.bookingId);
    // Fire-and-forget: marking read shouldn't block showing the thread.
    unawaited(repository.markConversationRead(widget.bookingId));
    return page;
  }

  void _reload() {
    setState(() => _future = _loadInitial());
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _sendText() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    setState(() => _isBusy = true);
    try {
      await ref.read(messagingRepositoryProvider).sendTextMessage(widget.bookingId, text);
      _textController.clear();
      if (mounted) _reload();
    } on MessagingException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _sendImage() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (picked == null) return;

    setState(() => _isBusy = true);
    try {
      final bytes = await picked.readAsBytes();
      await ref
          .read(messagingRepositoryProvider)
          .sendImageMessage(
            bookingId: widget.bookingId,
            bytes: bytes,
            filename: picked.name,
            contentType: picked.mimeType ?? 'image/jpeg',
          );
      if (mounted) _reload();
    } on MessagingException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _report(String messageId) async {
    final reason = await showReportReasonDialog(context, title: 'Report message');
    if (reason == null) return;
    try {
      await ref.read(messagingRepositoryProvider).reportMessage(messageId, reason: reason);
      if (mounted) AppSnackBar.showSuccess(context, 'Message reported.');
    } on MessagingException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conversation')),
      body: FutureBuilder<MessagePageData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading messages…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as MessagingException?)?.message ??
                  'Could not load this conversation.',
              onRetry: _reload,
            );
          }

          final messages = snapshot.data!.items;
          return Column(
            children: [
              Expanded(
                child: messages.isEmpty
                    ? const Center(child: Text('No messages yet. Say hello!'))
                    : ListView.builder(
                        reverse: true,
                        padding: const EdgeInsets.all(Spacing.s4),
                        itemCount: messages.length,
                        itemBuilder: (context, index) {
                          final message = messages[index];
                          return Padding(
                            padding: const EdgeInsets.only(bottom: Spacing.s2),
                            child: AppCard(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  if (message.body != null) Text(message.body!),
                                  if (message.attachmentUrl != null)
                                    Padding(
                                      padding: const EdgeInsets.only(top: Spacing.s2),
                                      child: Image.network(
                                        message.attachmentUrl!,
                                        height: 160,
                                        width: 160,
                                        fit: BoxFit.cover,
                                      ),
                                    ),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        '${message.createdAt.toLocal()} · ${message.isRead ? 'Read' : 'Sent'}',
                                        style: Theme.of(context).textTheme.bodySmall,
                                      ),
                                      TextButton(
                                        onPressed: () => _report(message.id),
                                        child: const Text('Report'),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
              ),
              SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(Spacing.s2),
                  child: Row(
                    children: [
                      IconButton(
                        onPressed: _isBusy ? null : _sendImage,
                        icon: const Icon(Icons.image_outlined),
                      ),
                      Expanded(
                        child: TextField(
                          controller: _textController,
                          decoration: const InputDecoration(hintText: 'Write a message…'),
                          minLines: 1,
                          maxLines: 4,
                        ),
                      ),
                      IconButton(
                        onPressed: _isBusy ? null : _sendText,
                        icon: const Icon(Icons.send),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
