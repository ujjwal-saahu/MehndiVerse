import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_models.dart';
import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'community_models.dart';
import 'community_repository.dart';

/// A minimal "report this" action shared by design/comment/user reporting
/// on mobile — see docs/community-and-trust.md#5-reports-enter-a-
/// moderation-queue. Mirrors the report-message pattern already used in
/// features/messages/conversation_detail_screen.dart.
class ReportAction extends ConsumerStatefulWidget {
  const ReportAction({required this.dialogTitle, required this.onReport, this.label = 'Report', super.key});

  final String dialogTitle;
  final String label;
  final Future<void> Function(String reason) onReport;

  @override
  ConsumerState<ReportAction> createState() => _ReportActionState();
}

class _ReportActionState extends ConsumerState<ReportAction> {
  bool _isBusy = false;

  Future<void> _submit() async {
    final reason = await showReportReasonDialog(context, title: widget.dialogTitle);
    if (reason == null) return;
    setState(() => _isBusy = true);
    try {
      await widget.onReport(reason);
      if (mounted) AppSnackBar.showSuccess(context, 'Thanks — our team will take a look.');
    } on CommunityException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: _isBusy ? null : _submit,
      child: Text(widget.label),
    );
  }
}

/// Design comments and (single-level) replies — see
/// docs/community-and-trust.md#1-design-comments-and-replies. Mirrors
/// apps/web/src/components/gallery/comments-section.tsx.
class CommentsSection extends ConsumerStatefulWidget {
  const CommentsSection({required this.designId, super.key});

  final String designId;

  @override
  ConsumerState<CommentsSection> createState() => _CommentsSectionState();
}

class _CommentsSectionState extends ConsumerState<CommentsSection> {
  late Future<List<CommentData>> _future;
  final _composerController = TextEditingController();
  String? _replyingToCommentId;
  bool _isPosting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _composerController.dispose();
    super.dispose();
  }

  void _load() {
    setState(() {
      _future = ref.read(communityRepositoryProvider).fetchComments(widget.designId);
    });
  }

  String? get _currentUserId {
    final authState = ref.read(authControllerProvider);
    return authState is AuthStateAuthenticated ? authState.user.id : null;
  }

  Future<void> _post({required String body, String? parentCommentId}) async {
    if (body.trim().isEmpty || _isPosting) return;
    setState(() => _isPosting = true);
    try {
      await ref
          .read(communityRepositoryProvider)
          .createComment(widget.designId, body: body.trim(), parentCommentId: parentCommentId);
      _composerController.clear();
      setState(() => _replyingToCommentId = null);
      _load();
    } on CommunityException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isPosting = false);
    }
  }

  Future<void> _delete(String commentId) async {
    try {
      await ref.read(communityRepositoryProvider).deleteComment(commentId);
      _load();
    } on CommunityException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    }
  }

  Future<void> _reportComment(String commentId, String reason) {
    return ref.read(communityRepositoryProvider).reportComment(commentId, reason: reason);
  }

  Future<void> _edit(String commentId, String currentBody) async {
    final controller = TextEditingController(text: currentBody);
    final newBody = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit comment'),
        content: TextField(controller: controller, autofocus: true, maxLines: 3),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (newBody == null || newBody.isEmpty) return;
    try {
      await ref.read(communityRepositoryProvider).updateComment(commentId, body: newBody);
      _load();
    } on CommunityException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Comments', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: Spacing.s2),
        TextField(
          controller: _composerController,
          maxLines: 2,
          decoration: const InputDecoration(hintText: 'Add a comment…'),
        ),
        const SizedBox(height: Spacing.s1),
        Align(
          alignment: Alignment.centerLeft,
          child: AppSecondaryButton(
            label: _isPosting ? 'Posting…' : 'Post',
            isLoading: _isPosting,
            onPressed: () => _post(body: _composerController.text),
          ),
        ),
        const SizedBox(height: Spacing.s4),
        FutureBuilder<List<CommentData>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const AppLoadingView(message: 'Loading comments…');
            }
            if (snapshot.hasError) {
              return AppErrorState(
                message: (snapshot.error as CommunityException?)?.message ??
                    'Could not load comments.',
                onRetry: _load,
              );
            }
            final comments = snapshot.data!;
            if (comments.isEmpty) {
              return const Text('No comments yet. Be the first to say something.');
            }
            return Column(
              children: [
                for (final comment in comments) ...[
                  _CommentTile(
                    id: comment.id,
                    userId: comment.userId,
                    userDisplayName: comment.userDisplayName,
                    body: comment.body,
                    currentUserId: _currentUserId,
                    onEdit: _edit,
                    onDelete: _delete,
                    onReport: _reportComment,
                  ),
                  for (final reply in comment.replies)
                    Padding(
                      padding: const EdgeInsets.only(left: Spacing.s6),
                      child: _CommentTile(
                        id: reply.id,
                        userId: reply.userId,
                        userDisplayName: reply.userDisplayName,
                        body: reply.body,
                        currentUserId: _currentUserId,
                        onEdit: _edit,
                        onDelete: _delete,
                        onReport: _reportComment,
                      ),
                    ),
                  if (_replyingToCommentId == comment.id)
                    Padding(
                      padding: const EdgeInsets.only(left: Spacing.s6, top: Spacing.s1),
                      child: _ReplyComposer(
                        onSubmit: (body) => _post(body: body, parentCommentId: comment.id),
                      ),
                    )
                  else
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () => setState(() => _replyingToCommentId = comment.id),
                        child: const Text('Reply'),
                      ),
                    ),
                  const Divider(),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

class _ReplyComposer extends StatefulWidget {
  const _ReplyComposer({required this.onSubmit});

  final Future<void> Function(String body) onSubmit;

  @override
  State<_ReplyComposer> createState() => _ReplyComposerState();
}

class _ReplyComposerState extends State<_ReplyComposer> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _controller,
            decoration: const InputDecoration(hintText: 'Write a reply…'),
          ),
        ),
        TextButton(
          onPressed: () => widget.onSubmit(_controller.text),
          child: const Text('Reply'),
        ),
      ],
    );
  }
}

class _CommentTile extends StatelessWidget {
  const _CommentTile({
    required this.id,
    required this.userId,
    required this.userDisplayName,
    required this.body,
    required this.currentUserId,
    required this.onEdit,
    required this.onDelete,
    required this.onReport,
  });

  final String id;
  final String userId;
  final String? userDisplayName;
  final String body;
  final String? currentUserId;
  final void Function(String id, String currentBody) onEdit;
  final void Function(String id) onDelete;
  final Future<void> Function(String id, String reason) onReport;

  @override
  Widget build(BuildContext context) {
    final isOwner = currentUserId != null && currentUserId == userId;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(body),
        Row(
          children: [
            Text(
              userDisplayName ?? 'Someone',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (isOwner) ...[
              TextButton(onPressed: () => onEdit(id, body), child: const Text('Edit')),
              TextButton(onPressed: () => onDelete(id), child: const Text('Delete')),
            ] else
              ReportAction(
                dialogTitle: 'Report comment',
                label: 'Report',
                onReport: (reason) => onReport(id, reason),
              ),
          ],
        ),
      ],
    );
  }
}

/// Reviews for an artist — see docs/community-and-trust.md#3 and #4.
/// Mirrors apps/web/src/components/gallery/reviews-section.tsx.
class ReviewsSection extends ConsumerStatefulWidget {
  const ReviewsSection({required this.artistProfileId, super.key});

  final String artistProfileId;

  @override
  ConsumerState<ReviewsSection> createState() => _ReviewsSectionState();
}

class _ReviewsSectionState extends ConsumerState<ReviewsSection> {
  late Future<ReviewListData> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(communityRepositoryProvider).fetchArtistReviews(widget.artistProfileId);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Reviews', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: Spacing.s2),
        FutureBuilder<ReviewListData>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const AppLoadingView(message: 'Loading reviews…');
            }
            if (snapshot.hasError) {
              return const Text('Could not load reviews.');
            }
            final reviews = snapshot.data!.items;
            if (reviews.isEmpty) {
              return const Text('No reviews yet.');
            }
            return Column(
              children: [
                for (final review in reviews)
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('★' * review.rating + '☆' * (5 - review.rating)),
                        if (review.body != null) ...[
                          const SizedBox(height: Spacing.s1),
                          Text(review.body!),
                        ],
                        const SizedBox(height: Spacing.s1),
                        Text(
                          review.customerDisplayName ?? 'A customer',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

/// Review-submission form for a completed booking — see
/// docs/community-and-trust.md#3-review-a-completed-booking. Mirrors
/// apps/web's booking-review-form.tsx.
class BookingReviewForm extends ConsumerStatefulWidget {
  const BookingReviewForm({required this.bookingId, super.key});

  final String bookingId;

  @override
  ConsumerState<BookingReviewForm> createState() => _BookingReviewFormState();
}

class _BookingReviewFormState extends ConsumerState<BookingReviewForm> {
  int _rating = 0;
  final _bodyController = TextEditingController();
  bool _isSubmitting = false;
  bool _isDone = false;

  @override
  void dispose() {
    _bodyController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating < 1 || _isSubmitting) return;
    setState(() => _isSubmitting = true);
    try {
      await ref
          .read(communityRepositoryProvider)
          .createReview(
            widget.bookingId,
            rating: _rating,
            body: _bodyController.text.trim().isEmpty ? null : _bodyController.text.trim(),
          );
      if (mounted) setState(() => _isDone = true);
    } on CommunityException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isDone) {
      return const Text('Thanks for your review!');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Leave a review', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: Spacing.s2),
        Row(
          children: [
            for (var value = 1; value <= 5; value++)
              IconButton(
                icon: Icon(value <= _rating ? Icons.star : Icons.star_border),
                onPressed: () => setState(() => _rating = value),
              ),
          ],
        ),
        TextField(
          controller: _bodyController,
          maxLines: 3,
          decoration: const InputDecoration(hintText: 'Tell others about your experience (optional)'),
        ),
        const SizedBox(height: Spacing.s2),
        AppPrimaryButton(
          label: 'Submit review',
          isLoading: _isSubmitting,
          onPressed: _rating < 1 ? null : _submit,
        ),
      ],
    );
  }
}
