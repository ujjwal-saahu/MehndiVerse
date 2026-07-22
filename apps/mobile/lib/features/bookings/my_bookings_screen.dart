import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'booking_models.dart';
import 'booking_repository.dart';

/// "My Bookings" — the customer's own booking history. See
/// docs/booking-lifecycle.md. The artist-side inbox stays the placeholder
/// screen at `/artist/bookings` this phase — see booking_models.dart's
/// module doc for why.
class MyBookingsScreen extends ConsumerStatefulWidget {
  const MyBookingsScreen({super.key});

  @override
  ConsumerState<MyBookingsScreen> createState() => _MyBookingsScreenState();
}

class _MyBookingsScreenState extends ConsumerState<MyBookingsScreen> {
  late Future<List<BookingSummaryData>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(bookingRepositoryProvider).fetchMyBookings();
  }

  void _reload() {
    setState(() {
      _future = ref.read(bookingRepositoryProvider).fetchMyBookings();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My bookings')),
      body: FutureBuilder<List<BookingSummaryData>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading bookings…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as BookingException?)?.message ??
                  'Could not load your bookings.',
              onRetry: _reload,
            );
          }

          final bookings = snapshot.data!;
          if (bookings.isEmpty) {
            return const PlaceholderScreen(
              title: 'Bookings',
              message:
                  "You haven't started a booking yet. Visit an artist's profile to request one.",
              icon: Icons.event_available_outlined,
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(Spacing.s4),
            itemCount: bookings.length,
            separatorBuilder: (context, index) => const SizedBox(height: Spacing.s2),
            itemBuilder: (context, index) {
              final booking = bookings[index];
              return AppCard(
                onTap: () => context.push('/bookings/${booking.id}'),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            [
                              booking.artistDisplayName ?? 'Artist',
                              if (booking.serviceName != null) booking.serviceName!,
                            ].join(' · '),
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          const SizedBox(height: Spacing.s1),
                          Text(
                            booking.requestedDate ?? 'No date set yet',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    Chip(label: Text(bookingStatusLabels[booking.status] ?? booking.status)),
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
