import 'package:flutter/material.dart';

/// Shows a standard confirm/cancel dialog and returns `true` if the user
/// confirmed. Centralizing this avoids every "are you sure?" flow
/// (e.g. account deletion, logout) re-implementing its own AlertDialog.
Future<bool> showAppConfirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'Confirm',
  String cancelLabel = 'Cancel',
  bool isDestructive = false,
}) async {
  final theme = Theme.of(context);
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(cancelLabel),
        ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(true),
          style: isDestructive
              ? TextButton.styleFrom(foregroundColor: theme.colorScheme.error)
              : null,
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return confirmed ?? false;
}

/// Shows a "why are you reporting this?" dialog and returns the trimmed
/// reason, or `null` if the user cancelled or left it blank — shared by
/// every report surface (design/comment/user/message) so they all prompt
/// the same way. See docs/community-and-trust.md#5-reports-enter-a-
/// moderation-queue.
Future<String?> showReportReasonDialog(BuildContext context, {required String title}) async {
  final controller = TextEditingController();
  final reason = await showDialog<String>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: controller,
        autofocus: true,
        maxLines: 3,
        decoration: const InputDecoration(hintText: 'Reason'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        TextButton(
          onPressed: () => Navigator.of(context).pop(controller.text.trim()),
          child: const Text('Report'),
        ),
      ],
    ),
  );
  if (reason == null || reason.isEmpty) return null;
  return reason;
}
