import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../bookings/booking_repository.dart';
import '../community/community_widgets.dart';
import '../gallery/gallery_widgets.dart';
import 'artist_directory_models.dart';
import 'artist_repository.dart';
import 'artist_scheduling_models.dart';

/// Public artist profile — see docs/artist-directory.md. Mirrors the web
/// app's src/app/(marketing)/artists/[id]/page.tsx.
class ArtistPublicProfileScreen extends ConsumerStatefulWidget {
  const ArtistPublicProfileScreen({required this.artistId, super.key});

  final String artistId;

  @override
  ConsumerState<ArtistPublicProfileScreen> createState() => _ArtistPublicProfileScreenState();
}

class _ArtistPublicProfileScreenState extends ConsumerState<ArtistPublicProfileScreen> {
  late Future<ArtistPublicProfileData> _future;
  bool _isTogglingFollow = false;

  String? _selectedServiceId;
  AvailableSlotsData? _slots;
  bool _isCheckingAvailability = false;
  ArtistException? _availabilityError;
  bool _isRequestingBooking = false;

  @override
  void initState() {
    super.initState();
    _future = ref.read(artistRepositoryProvider).fetchPublicProfile(widget.artistId);
  }

  void _reload() {
    setState(() {
      _future = ref.read(artistRepositoryProvider).fetchPublicProfile(widget.artistId);
    });
  }

  Future<void> _toggleFollow(ArtistPublicProfileData artist) async {
    setState(() => _isTogglingFollow = true);
    final repository = ref.read(artistRepositoryProvider);
    try {
      if (artist.isFollowed) {
        await repository.unfollowArtist(artist.id);
      } else {
        await repository.followArtist(artist.id);
      }
      if (!mounted) return;
      setState(() {
        _future = Future.value(
          artist.copyWith(
            isFollowed: !artist.isFollowed,
            followerCount: artist.isFollowed
                ? artist.followerCount - 1
                : artist.followerCount + 1,
          ),
        );
      });
    } on ArtistException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isTogglingFollow = false);
    }
  }

  /// Read-only slot browsing — see docs/artist-scheduling.md. Booking
  /// creation itself is the separate "Request a booking" action below.
  Future<void> _checkAvailability(String artistId) async {
    if (_selectedServiceId == null) return;
    setState(() {
      _isCheckingAvailability = true;
      _availabilityError = null;
    });
    try {
      final today = DateTime.now();
      final slots = await ref
          .read(artistRepositoryProvider)
          .fetchAvailableSlots(
            artistId: artistId,
            serviceId: _selectedServiceId!,
            startDate: today,
            endDate: today.add(const Duration(days: 6)),
          );
      if (!mounted) return;
      setState(() => _slots = slots);
    } on ArtistException catch (e) {
      if (!mounted) return;
      setState(() => _availabilityError = e);
    } finally {
      if (mounted) setState(() => _isCheckingAvailability = false);
    }
  }

  /// Creates a `draft` booking against this artist and pushes the
  /// detail/edit screen — see docs/booking-lifecycle.md#3.
  Future<void> _requestBooking(String artistId) async {
    setState(() => _isRequestingBooking = true);
    try {
      final booking = await ref
          .read(bookingRepositoryProvider)
          .createDraft(artistProfileId: artistId);
      if (!mounted) return;
      context.push('/bookings/${booking.id}');
    } on BookingException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isRequestingBooking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Artist')),
      body: FutureBuilder<ArtistPublicProfileData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const AppLoadingView(message: 'Loading profile…');
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: (snapshot.error as ArtistException?)?.message ??
                  'Could not load this artist.',
              onRetry: _reload,
            );
          }

          final artist = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(Spacing.s4),
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: IconSizes.xl,
                    backgroundImage: artist.profileImageUrl != null
                        ? NetworkImage(artist.profileImageUrl!)
                        : null,
                    child: artist.profileImageUrl == null
                        ? const Icon(Icons.person, size: IconSizes.lg)
                        : null,
                  ),
                  const SizedBox(width: Spacing.s4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                artist.displayName,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                            ),
                            if (artist.isVerified) ...[
                              const SizedBox(width: Spacing.s1),
                              const Icon(Icons.verified, size: IconSizes.sm, color: Colors.blue),
                            ],
                          ],
                        ),
                        if (artist.headline != null) Text(artist.headline!),
                        Text(
                          artist.ratingCount > 0
                              ? '★ ${artist.ratingAverage.toStringAsFixed(1)} (${artist.ratingCount} reviews)'
                              : 'No reviews yet',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: Spacing.s4),
              Row(
                children: [
                  Expanded(
                    child: artist.isFollowed
                        ? AppSecondaryButton(
                            label: 'Following · ${artist.followerCount}',
                            isLoading: _isTogglingFollow,
                            onPressed: () => _toggleFollow(artist),
                          )
                        : AppPrimaryButton(
                            label: 'Follow · ${artist.followerCount}',
                            isLoading: _isTogglingFollow,
                            onPressed: () => _toggleFollow(artist),
                          ),
                  ),
                ],
              ),
              const SizedBox(height: Spacing.s2),
              // See docs/booking-lifecycle.md#3-booking-draft-and-submission.
              AppSecondaryButton(
                label: artist.isAcceptingBookings
                    ? 'Request a booking'
                    : 'Not accepting bookings',
                isLoading: _isRequestingBooking,
                onPressed: artist.isAcceptingBookings
                    ? () => _requestBooking(artist.id)
                    : null,
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: ReportAction(
                  dialogTitle: 'Report artist',
                  label: 'Report artist',
                  onReport: (reason) => ref
                      .read(communityRepositoryProvider)
                      .reportUser(artist.userId, reason: reason),
                ),
              ),
              if (artist.bio != null) ...[
                const SizedBox(height: Spacing.s4),
                Text(artist.bio!),
              ],
              if (artist.serviceAreas.isNotEmpty || artist.languages.isNotEmpty) ...[
                const SizedBox(height: Spacing.s4),
                if (artist.serviceAreas.isNotEmpty)
                  Text('Service areas: ${artist.serviceAreas.join(', ')}'),
                if (artist.languages.isNotEmpty)
                  Text('Languages: ${artist.languages.join(', ')}'),
              ],
              if (artist.services.isNotEmpty) ...[
                const SizedBox(height: Spacing.s6),
                Text('Services', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: Spacing.s2),
                for (final service in artist.services)
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(service.name, style: Theme.of(context).textTheme.titleSmall),
                        if (service.description != null) Text(service.description!),
                        Text(_formatPrice(service)),
                      ],
                    ),
                  ),
              ],
              if (artist.services.any((s) => s.durationMinutes != null)) ...[
                const SizedBox(height: Spacing.s6),
                Text('Check availability', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: Spacing.s2),
                _buildCheckAvailability(artist),
              ],
              if (artist.availabilityPreview.isNotEmpty) ...[
                const SizedBox(height: Spacing.s6),
                Text('Availability', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: Spacing.s2),
                Wrap(
                  spacing: Spacing.s2,
                  children: [
                    for (final slot in artist.availabilityPreview)
                      Chip(
                        label: Text(
                          '${dayNames[slot.dayOfWeek]} ${slot.startTime.substring(0, 5)}–${slot.endTime.substring(0, 5)}',
                        ),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: Spacing.s6),
              Text('Portfolio', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: Spacing.s2),
              if (artist.portfolioPreview.isEmpty)
                const Text('No published designs yet.')
              else
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    mainAxisSpacing: Spacing.s2,
                    crossAxisSpacing: Spacing.s2,
                    childAspectRatio: 0.85,
                  ),
                  itemCount: artist.portfolioPreview.length,
                  itemBuilder: (context, index) =>
                      DesignThumbnailCard(design: artist.portfolioPreview[index]),
                ),
              const SizedBox(height: Spacing.s6),
              ReviewsSection(artistProfileId: artist.id),
            ],
          );
        },
      ),
    );
  }

  Widget _buildCheckAvailability(ArtistPublicProfileData artist) {
    final bookableServices = artist.services.where((s) => s.durationMinutes != null).toList();
    final selectedId = _selectedServiceId ?? bookableServices.first.id;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: DropdownButton<String>(
                isExpanded: true,
                value: selectedId,
                items: [
                  for (final service in bookableServices)
                    DropdownMenuItem(value: service.id, child: Text(service.name)),
                ],
                onChanged: (value) => setState(() {
                  _selectedServiceId = value;
                  _slots = null;
                }),
              ),
            ),
            const SizedBox(width: Spacing.s2),
            AppSecondaryButton(
              label: 'Check',
              isLoading: _isCheckingAvailability,
              onPressed: () {
                setState(() => _selectedServiceId = selectedId);
                _checkAvailability(artist.id);
              },
            ),
          ],
        ),
        if (_availabilityError != null) ...[
          const SizedBox(height: Spacing.s2),
          Text(_availabilityError!.message, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ],
        if (_slots != null) ...[
          const SizedBox(height: Spacing.s2),
          if (_slots!.slots.isEmpty)
            const Text('No open slots in the next week.')
          else
            Wrap(
              spacing: Spacing.s2,
              runSpacing: Spacing.s2,
              children: [
                for (final slot in _slots!.slots)
                  Chip(label: Text(_formatSlotLocal(slot.start))),
              ],
            ),
          const SizedBox(height: Spacing.s1),
          const Text(
            "Times shown in your device's local timezone. Use \"Request a booking\" "
            "above to start a request — this preview doesn't book a specific slot.",
            style: TextStyle(fontSize: FontSizes.xs),
          ),
        ],
      ],
    );
  }

  String _formatSlotLocal(DateTime utcStart) {
    final local = utcStart.toLocal();
    final hour12 = local.hour % 12 == 0 ? 12 : local.hour % 12;
    final minute = local.minute.toString().padLeft(2, '0');
    final period = local.hour < 12 ? 'AM' : 'PM';
    return '${local.month}/${local.day} $hour12:$minute $period';
  }

  String _formatPrice(ArtistServiceData service) {
    switch (service.pricingType) {
      case 'fixed':
        return service.priceAmount != null
            ? '${service.currency} ${service.priceAmount}'
            : '—';
      case 'range':
        return '${service.currency} ${service.priceMin ?? '?'} – ${service.priceMax ?? '?'}';
      default:
        return 'Custom quote';
    }
  }
}
