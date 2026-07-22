import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../community/community_widgets.dart';
import 'booking_models.dart';
import 'booking_repository.dart';

const _rescheduleableStatuses = {
  'requested',
  'artist_reviewing',
  'quotation_sent',
  'customer_reviewing',
  'confirmed',
  'deposit_pending',
  'deposit_paid',
};

const _cancellableStatuses = {
  'draft',
  'requested',
  'artist_reviewing',
  'quotation_sent',
  'customer_reviewing',
  'confirmed',
  'deposit_pending',
  'deposit_paid',
  'in_progress',
};

/// Booking detail/edit — see docs/booking-lifecycle.md. Draft editing here is
/// deliberately minimal (date/time/notes only, via simple dialogs) rather
/// than mirroring the full multi-field web form — a customer who wants the
/// complete request form can use the web app; this screen focuses on
/// tracking status, quotes, and the shared cancel/reschedule actions.
class BookingDetailScreen extends ConsumerStatefulWidget {
  const BookingDetailScreen({required this.bookingId, super.key});

  final String bookingId;

  @override
  ConsumerState<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends ConsumerState<BookingDetailScreen> {
  late Future<BookingDetailData> _future;
  bool _isBusy = false;

  @override
  void initState() {
    super.initState();
    _future = ref.read(bookingRepositoryProvider).fetchBooking(widget.bookingId);
  }

  void _reload() {
    setState(() {
      _future = ref.read(bookingRepositoryProvider).fetchBooking(widget.bookingId);
    });
  }

  Future<void> _run(Future<BookingDetailData> Function() action) async {
    setState(() => _isBusy = true);
    try {
      final updated = await action();
      if (!mounted) return;
      setState(() {
        _future = Future.value(updated);
      });
    } on BookingException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _submit() =>
      _run(() => ref.read(bookingRepositoryProvider).submitBooking(widget.bookingId));

  Future<void> _cancel() async {
    final reason = await _promptText('Reason for cancelling (optional)');
    await _run(
      () => ref.read(bookingRepositoryProvider).cancelBooking(widget.bookingId, reason: reason),
    );
  }

  Future<void> _reschedule() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked == null) return;
    final newDate =
        '${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
    await _run(
      () => ref
          .read(bookingRepositoryProvider)
          .rescheduleBooking(widget.bookingId, newDate: newDate),
    );
  }

  Future<void> _acceptQuote(String quoteId) => _run(
    () => ref.read(bookingRepositoryProvider).acceptQuote(widget.bookingId, quoteId),
  );

  Future<void> _rejectQuote(String quoteId) async {
    final reason = await _promptText('Reason for declining (optional)');
    await _run(
      () => ref.read(bookingRepositoryProvider).rejectQuote(widget.bookingId, quoteId, reason: reason),
    );
  }

  Future<String?> _promptText(String hint) {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        content: TextField(controller: controller, autofocus: true, decoration: InputDecoration(hintText: hint)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Skip'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Booking')),
      body: FutureBuilder<BookingDetailData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading booking…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as BookingException?)?.message ?? 'Could not load this booking.',
              onRetry: _reload,
            );
          }

          final booking = snapshot.data!;
          final pendingQuotes = booking.quotes.where((q) => q.status == 'pending');
          final pendingQuoteId = pendingQuotes.isEmpty ? null : pendingQuotes.first.id;

          return ListView(
            padding: const EdgeInsets.all(Spacing.s4),
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      booking.artistDisplayName ?? 'Artist',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Chip(label: Text(bookingStatusLabels[booking.status] ?? booking.status)),
                ],
              ),
              if (booking.serviceName != null) ...[
                const SizedBox(height: Spacing.s1),
                Text(booking.serviceName!, style: Theme.of(context).textTheme.bodyMedium),
              ],
              const SizedBox(height: Spacing.s4),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Date: ${booking.requestedDate ?? "Not set"}'),
                    if (booking.requestedTime != null)
                      Text('Time: ${booking.requestedTime!.substring(0, 5)}'),
                    if (booking.locationType != null) Text('Location: ${booking.locationType}'),
                    if (booking.totalAmount != null)
                      Text('Total: ${booking.currency} ${booking.totalAmount}'),
                    if (booking.depositAmount != null)
                      Text('Deposit: ${booking.currency} ${booking.depositAmount}'),
                  ],
                ),
              ),
              if (booking.status == 'draft') ...[
                const SizedBox(height: Spacing.s4),
                AppPrimaryButton(
                  label: 'Submit request',
                  isLoading: _isBusy,
                  onPressed: _submit,
                ),
              ],
              if (booking.quotes.isNotEmpty) ...[
                const SizedBox(height: Spacing.s6),
                Text('Quotes', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: Spacing.s2),
                for (final quote in booking.quotes)
                  AppCard(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text('${quote.currency} ${quote.amount} — ${quote.status}'),
                        ),
                        if (quote.status == 'pending' && pendingQuoteId == quote.id) ...[
                          TextButton(
                            onPressed: _isBusy ? null : () => _acceptQuote(quote.id),
                            child: const Text('Accept'),
                          ),
                          TextButton(
                            onPressed: _isBusy ? null : () => _rejectQuote(quote.id),
                            child: const Text('Decline'),
                          ),
                        ],
                      ],
                    ),
                  ),
              ],
              if (_rescheduleableStatuses.contains(booking.status)) ...[
                const SizedBox(height: Spacing.s6),
                AppSecondaryButton(
                  label: 'Request reschedule',
                  isLoading: _isBusy,
                  onPressed: _reschedule,
                ),
              ],
              if (_cancellableStatuses.contains(booking.status)) ...[
                const SizedBox(height: Spacing.s2),
                AppSecondaryButton(label: 'Cancel booking', isLoading: _isBusy, onPressed: _cancel),
              ],
              if (booking.status == 'completed') ...[
                const SizedBox(height: Spacing.s6),
                BookingReviewForm(bookingId: booking.id),
              ],
              const SizedBox(height: Spacing.s6),
              Text('History', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: Spacing.s2),
              for (final entry in booking.statusHistory)
                Padding(
                  padding: const EdgeInsets.only(bottom: Spacing.s2),
                  child: Text(
                    entry.fromStatus != null
                        ? '${bookingStatusLabels[entry.fromStatus] ?? entry.fromStatus} → ${bookingStatusLabels[entry.toStatus] ?? entry.toStatus}'
                        : 'Created as ${bookingStatusLabels[entry.toStatus] ?? entry.toStatus}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
